import smartpy as sp

t_balance_of_args = sp.TRecord(
    requests=sp.TList(sp.TRecord(owner=sp.TAddress, token_id=sp.TNat)),
    callback=sp.TContract(
        sp.TList(
            sp.TRecord(
                request=sp.TRecord(owner=sp.TAddress, token_id=sp.TNat), balance=sp.TNat
            ).layout(("request", "balance"))
        )
    ),
).layout(("requests", "callback"))

class Fa2NftMinimal(sp.Contract):
    """Minimal FA2 contract for NFTs.
    This is a minimal self contained implementation example showing how to
    implement an NFT contract following the FA2 standard in SmartPy. It is for
    illustrative purposes only. For a more flexible toolbox aimed at real world
    applications please refer to FA2_lib."
    """

    def __init__(self, administrator, metadata_base, metadata_url):
        self.init(
            administrator=administrator,
            ledger=sp.big_map(tkey=sp.TNat, tvalue=sp.TAddress),
            metadata=sp.utils.metadata_of_url(metadata_url),
            next_token_id=sp.nat(0),
            auction_contract = sp.address("tz1hdQscorfqMzFqYxnrApuS5i6QSTuoAp3w"),
            winner = sp.address("tz1hdQscorfqMzFqYxnrApuS5i6QSTuoAp3w"),
            operators=sp.big_map(
                tkey=sp.TRecord(
                    owner=sp.TAddress,
                    operator=sp.TAddress,
                    token_id=sp.TNat,
                ).layout(("owner", ("operator", "token_id"))),
                tvalue=sp.TUnit,
            ),
            token_metadata=sp.big_map(
                tkey=sp.TNat,
                tvalue=sp.TRecord(
                    token_id=sp.TNat,
                    token_info=sp.TMap(sp.TString, sp.TBytes),
                ),
            ),
        )
        metadata_base["views"] = [
            self.all_tokens,
            self.get_balance,
            self.is_operator,
            self.total_supply,
        ]
        self.init_metadata("metadata_base", metadata_base)

    @sp.entry_point
    def transfer(self, batch):
        """Accept a list of transfer operations.
        Each transfer operation specifies a source: `from_` and a list
        of transactions. Each transaction specifies the destination: `to_`,
        the `token_id` and the `amount` to be transferred.
        Args:
            batch: List of transfer operations.
        Raises:
            `FA2_TOKEN_UNDEFINED`, `FA2_NOT_OPERATOR`, `FA2_INSUFFICIENT_BALANCE`
        """
        with sp.for_("transfer", batch) as transfer:
            with sp.for_("tx", transfer.txs) as tx:
                sp.set_type(
                    tx,
                    sp.TRecord(
                        to_=sp.TAddress, token_id=sp.TNat, amount=sp.TNat
                    ).layout(("to_", ("token_id", "amount"))),
                )
                sp.verify(tx.token_id < self.data.next_token_id, "FA2_TOKEN_UNDEFINED")
                sp.verify(
                    (transfer.from_ == sp.sender)
                    | self.data.operators.contains(
                        sp.record(
                            owner=transfer.from_,
                            operator=sp.sender,
                            token_id=tx.token_id,
                        )
                    ),
                    "FA2_NOT_OPERATOR",
                )
                with sp.if_(tx.amount > 0):
                    sp.verify(
                        (tx.amount == 1)
                        & (self.data.ledger[tx.token_id] == transfer.from_),
                        "FA2_INSUFFICIENT_BALANCE",
                    )
                    self.data.ledger[tx.token_id] = tx.to_

    @sp.entry_point
    def update_operators(self, actions):
        """Accept a list of variants to add or remove operators.
        Operators can perform transfer on behalf of the owner.
        Owner is a Tezos address which can hold tokens.
        Only the owner can change its operators.
        Args:
            actions: List of operator update actions.
        Raises:
            `FA2_NOT_OWNER`
        """
        with sp.for_("update", actions) as action:
            with action.match_cases() as arg:
                with arg.match("add_operator") as operator:
                    sp.verify(operator.owner == sp.sender, "FA2_NOT_OWNER")
                    self.data.operators[operator] = sp.unit
                with arg.match("remove_operator") as operator:
                    sp.verify(operator.owner == sp.sender, "FA2_NOT_OWNER")
                    del self.data.operators[operator]

    @sp.entry_point
    def balance_of(self, args):
        """Send the balance of multiple account / token pairs to a callback
        address.
        transfer 0 mutez to `callback` with corresponding response.
        Args:
            callback (contract): Where to callback the answer.
            requests: List of requested balances.
        Raises:
            `FA2_TOKEN_UNDEFINED`, `FA2_CALLBACK_NOT_FOUND`
        """

        def f_process_request(req):
            sp.verify(req.token_id < self.data.next_token_id, "FA2_TOKEN_UNDEFINED")
            sp.result(
                sp.record(
                    request=sp.record(owner=req.owner, token_id=req.token_id),
                    balance=sp.eif(
                        self.data.ledger[req.token_id] == req.owner, sp.nat(1), 0
                    ),
                )
            )

        sp.set_type(args, t_balance_of_args)
        sp.transfer(args.requests.map(f_process_request), sp.mutez(0), args.callback)

    @sp.entry_point
    def mint(self, metadata):
        """(Admin only) Create a new token with an incremented id and assign
        it. to `to_`.
        Args:
            to_ (address): Receiver of the tokens.
            metadata (map of string bytes): Metadata of the token.
        Raises:
            `FA2_NOT_ADMIN`
        """
        sp.verify(sp.sender == self.data.administrator, "FA2_NOT_ADMIN")
        token_id = sp.compute(self.data.next_token_id)
        self.data.token_metadata[token_id] = sp.record(
            token_id=token_id, token_info=metadata
        )
        self.data.ledger[token_id] = self.data.winner
        self.data.next_token_id += 1
        self.data.winner = self.data.administrator

    @sp.entry_point
    def update_auction_address(self, auction_address):
        sp.verify(sp.sender == self.data.administrator, "Only admin can update this address")
        self.data.auction_contract = auction_address

    @sp.entry_point
    def store_to(self, to_):
        sp.verify(sp.sender == self.data.auction_contract, "You cannot store this address")
        self.data.winner = to_

    @sp.offchain_view(pure=True)
    def all_tokens(self):
        """Return the list of all the `token_id` known to the contract."""
        sp.result(sp.range(0, self.data.next_token_id))

    @sp.offchain_view(pure=True)
    def get_balance(self, params):
        """Return the balance of an address for the specified `token_id`."""
        sp.set_type(
            params,
            sp.TRecord(owner=sp.TAddress, token_id=sp.TNat).layout(
                ("owner", "token_id")
            ),
        )
        sp.verify(params.token_id < self.data.next_token_id, "FA2_TOKEN_UNDEFINED")
        sp.result(sp.eif(self.data.ledger[params.token_id] == params.owner, 1, 0))

    @sp.offchain_view(pure=True)
    def total_supply(self, params):
        """Return the total number of tokens for the given `token_id` if known
        or fail if not."""
        sp.verify(params.token_id < self.data.next_token_id, "FA2_TOKEN_UNDEFINED")
        sp.result(1)

    @sp.offchain_view(pure=True)
    def is_operator(self, params):
        """Return whether `operator` is allowed to transfer `token_id` tokens
        owned by `owner`."""
        sp.result(self.data.operators.contains(params))

metadata_base = {
    "name": "FA2 NFT minimal",
    "version": "1.0.0",
    "description": "This is a minimal implementation of FA2 (TZIP-012) using SmartPy.",
    "interfaces": ["TZIP-012", "TZIP-016"],
    "authors": ["SmartPy <https://smartpy.io/#contact>"],
    "homepage": "https://smartpy.io/ide?template=fa2_nft_minimal.py",
    "source": {
        "tools": ["SmartPy"],
        "location": "https://gitlab.com/SmartPy/smartpy/-/raw/master/python/templates/fa2_nft_minimal.py",
    },
    "permissions": {
        "operator": "owner-or-operator-transfer",
        "receiver": "owner-no-hook",
        "sender": "owner-no-hook",
    },
}

class Auction(sp.Contract):
    def __init__(self, owner):
        self.init(owner = owner, topBidder = owner, topBid = sp.tez(0), live = True, nft_contract = owner,
            bids = { owner: sp.tez(0) })

    @sp.entry_point
    def bid(self):
        sp.verify(self.data.live == True, "This auction has ended!")
        bids = self.data.bids
        sp.verify(~bids.contains(sp.sender), "You already bid, cancel first bid before bidding again")
        bids[sp.sender] = sp.amount
        sp.if sp.amount > bids[self.data.topBidder]:
            self.data.topBidder = sp.sender
            self.data.topBid = sp.amount
        sp.else:
            sp.failwith("You are bidding too low")

    @sp.entry_point
    def cancel_bid(self):
        sp.verify(self.data.bids.contains(sp.sender))
        sp.verify(sp.sender != self.data.topBidder, "You are the Top Bidder and can't cancel")
        sp.if self.data.bids[sp.sender] == sp.tez(0):
            del self.data.bids[sp.sender]
        sp.else:
            sp.send(sp.sender, self.data.bids[sp.sender])
            del self.data.bids[sp.sender]

    @sp.entry_point
    def update_nft_address(self, nft_address):
        sp.verify(sp.sender == self.data.owner, "Only admin can update this address")
        self.data.nft_contract = nft_address

    @sp.entry_point
    def end_auction(self):
        self.data.live = False
        winner_address_args_type = sp.TAddress
        store_winner_entry_point = sp.contract(winner_address_args_type, self.data.nft_contract, "store_to").open_some()
        sp.transfer(self.data.topBidder, sp.tez(0), store_winner_entry_point)
        self.data.topBidder = self.data.owner

    @sp.entry_point
    def restart_auction(self):
        self.data.live = True
        self.data.bids = sp.map(l = {self.data.owner : sp.tez(0) }, tkey = sp.TAddress, tvalue = sp.TMutez)
        sp.send(sp.sender, sp.balance)


if "templates" not in __name__:

    def make_metadata(symbol, name, decimals):
        """Helper function to build metadata JSON bytes values."""
        return sp.map(
            l={
                "decimals": sp.utils.bytes_of_string("%d" % decimals),
                "name": sp.utils.bytes_of_string(name),
                "symbol": sp.utils.bytes_of_string(symbol),
            }
        )
    
    @sp.add_test(name="Test")
    def test():
        admin = sp.address("tz1YUyK3aGum7oW29iLX2hRTraHUZP8C5b5r")
        alice = sp.test_account("Alice")
        bob = sp.test_account("Bob")
        harry = sp.test_account("Harry")
        scenario = sp.test_scenario()
        nft = Fa2NftMinimal(admin, metadata_base, "https://example.com")
        tok0_md = make_metadata(name="Token Zero", decimals=1, symbol="Tok0")
        tok1_md = make_metadata(name="Token One", decimals=2, symbol="Tok1")
        tok2_md = make_metadata(name="Token Two", decimals=3, symbol="Tok2")

        scenario.h1("NFT contract Origination")
        scenario += nft
        
        auc = Auction(admin)

        scenario.h1("Auction contract Origination")
        scenario += auc

        scenario.h1("Bids")
        scenario.h3("Alice successfully bids")
        scenario += auc.bid().run(sender=alice.address, amount=sp.tez(2))
        scenario.h3("Alice can't bid twice")
        scenario += auc.bid().run(sender=alice.address, amount=sp.tez(2), valid=False)
        scenario.h3("Bob bids too low")
        scenario += auc.bid().run(sender=bob.address, amount=sp.tez(1), valid=False)
        scenario.h3("Bob bids higher")
        scenario += auc.bid().run(sender=bob.address, amount=sp.tez(3))
        scenario.h3("Bob can't cancel when he is Top Bidder")
        scenario += auc.cancel_bid().run(sender=bob.address, valid=False)
        scenario.h3("Alice bids higher")
        scenario += auc.bid().run(sender=alice.address, amount=sp.tez(4), valid=False)
        scenario.h3("Alice cancels first bid")
        scenario += auc.cancel_bid().run(sender=alice.address)
        scenario.h3("Alice bids higher")
        scenario += auc.bid().run(sender=alice.address, amount=sp.tez(4))
        scenario.h3("Admin stores nft contract address in Auction")
        scenario += auc.update_nft_address(nft.address).run(sender=admin, amount=sp.tez(0))
        scenario.h3("Bob can't store nft contract address in Auction")
        scenario += auc.update_nft_address(nft.address).run(sender=bob.address, amount=sp.tez(0), valid=False)
        scenario.h3("Admin stores auction contract address in nft")
        scenario += nft.update_auction_address(auc.address).run(sender=admin, amount=sp.tez(0))
        scenario.h3("Bob can't store auction contract address in nft")
        scenario += nft.update_auction_address(auc.address).run(sender=bob.address, amount=sp.tez(0), valid=False)
        scenario.h3("Admin ends auction")
        scenario += auc.end_auction().run(sender=admin, amount=sp.tez(0))
        scenario.h3("Bob can't end auction")
        scenario += auc.end_auction().run(sender=bob.address, amount=sp.tez(0), valid=False)
        scenario.h3("Bob can't mint NFT")
        scenario += nft.mint(tok0_md).run(sender=bob.address, amount=sp.tez(0), valid=False)
        scenario.h3("Admin mints NFT")
        scenario += nft.mint(tok0_md).run(sender=admin, amount=sp.tez(0))
        scenario.h3("Admin restarts auction")
        scenario += auc.restart_auction().run(sender=admin, amount=sp.tez(0))
        scenario.h3("Harry successfully bids in the second auction")
        scenario += auc.bid().run(sender=harry.address, amount=sp.tez(2))
        scenario.h3("Alice bids")
        scenario += auc.bid().run(sender=alice.address, amount=sp.tez(5))
