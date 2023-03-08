# Pictor Auction and FA2 Contracts

------------

### Smart Contracts description

In this project I have written two contracts: An English Auction and a FA2. The purpose of these contracts is to have an english auction (highest bid wins) and the winner of the auction will be able to get the NFT in the FA2 contract.

In order to understand the contracts for the purpose of this project, I'm going to describe the process of auction and minting the winning NFT from start to finish. Also, we need to focus only on the auction contract and a few (not all) entrypoints on the FA2 contract. (It is a standard contract in Tezos, it beats the purpose of the project if the reviewer studies every entrypoint of the FA2 except the ones described in this ReadMe).

First we originate both contracts and the only originating parameter that they take is the admin’s address. After that, the admin can call “*update_nft_address*” in the auction to store the address of the FA2 contract and “*update_auction_address*” in the FA2 contract to store the address of the auction contract. They will need those addresses to call each-other’s entry points.

The auction process starts with bidding by using the “*bid*” entrypoint. Everyone can call it once by sending tez to the contract as a bid. It can be called again only after the user has canceled his first bid with the “*cancel_bid*” entrypoint. Also, it only takes bids that are higher than the current highest bid.

The “*cancel_bid*” entrypoint cancels the user's first bid so that he can bid again in an effort to beat the highest bidder. It sends back the tez of the first bid to the user’s wallet.

When enough time has passed, the auction can be stopped by calling the “*end_auction*” entrypoint. It ends the auction and deletes the bids. It also calls the “*store_to*” entrypoint in the FA2 contract, storing the winner’s address in the FA2 contract. Thus, when minting the NFT with the use of the “*mint*” entrypoint, this address will be used to send the token to.

Another round of the auction can be started by calling the “*restart_auction*” entrypoint and everything can start over once again to mint another NFT.

### Interacting with the Smart Contracts

In order to interact with the smart contracts, the reviewer will need at least two addresses that contain tez in the Ghostnet. Without admin privileges, those addresses can only interact with the “*bid*” and “*cancel_bid*” entry points. They don’t take any parameters, but you need to send tez in order to make your bid. (Remember that you will get an error if you send a lower amount than what the highest bid already is, and another error if you want to bid twice without canceling the first bid).

In order to fully interact with the smart contracts, the reviewer needs to deploy them in a testnet and feed his own address in the parameters, so that he can have admin access to all functions.

### All entry points with sample inputs

##### Admin only:

- update_nft_address - input: NFT Contract address
- update_auction_address - input: Auction Contract address
- mint - takes token metadata as input (a pair of string and bytes). Use an online tool to convert any string to bytes, like [this one](https://onlinestringtools.com/convert-string-to-bytes  "this one"), the string can be whatever, no need to be the same as the one generating the bytes.

##### Everyone:

- bid - no input, but need to send tez
- cancel_bid - no input
- end_auction - no input
- restart_auction - no input

##### Automatic:

- store_to

### Contract Addresses

English Auction - **KT1VmNmni6zJCz6RrZtPCZBsyrMhQBCNejHn**

FA2 - **KT1DgbWd3pakHMzUpc83ANSMdAQHr8VAVhB9**
