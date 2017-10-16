import os
import unittest

from dgas.test.base import AsyncHandlerTest
from tornado.testing import gen_test
from testing.common.database import get_path_of

from dgas.ethereum.contract import Contract

from dgas.test.ethereum.parity import requires_parity
from dgas.test.ethereum.faucet import FaucetMixin, FAUCET_PRIVATE_KEY

# from https://solidity.readthedocs.io/en/latest/solidity-by-example.html
VOTER_CONTRACT_SOURCECODE = """
pragma solidity ^0.4.0;

contract Ballot {
    struct Voter {
        uint weight;
        bool voted;
        address delegate;
        uint vote;
    }

    struct Proposal {
        bytes32 name;
        uint voteCount;
    }

    address public chairperson;

    mapping(address => Voter) public voters;

    Proposal[] public proposals;

    function Ballot(bytes32[] proposalNames) {
        chairperson = msg.sender;
        voters[chairperson].weight = 1;

        for (uint i = 0; i < proposalNames.length; i++) {
            proposals.push(Proposal({
                name: proposalNames[i],
                voteCount: 0
            }));
        }
    }

    function giveRightToVote(address voter) {
        if (msg.sender != chairperson || voters[voter].voted) {
            throw;
        }

        voters[voter].weight = 1;
    }

    function delegate(address to) {
        Voter sender = voters[msg.sender];
        if (sender.voted) throw;

        while (voters[to].delegate != address(0) && voters[to].delegate != msg.sender) {
            to = voters[to].delegate;
        }

        sender.voted = true;
        sender.delegate = to;
        Voter delegate = voters[to];
        if (delegate.voted) {
            proposals[delegate.vote].voteCount += sender.weight;
        } else {
            delegate.weight += sender.weight;
        }
    }

    function vote(uint proposal) {
        Voter sender = voters[msg.sender];
        if (sender.voted) throw;
        sender.voted = true;
        sender.vote = proposal;

        proposals[proposal].voteCount += sender.weight;
    }

    function winningProposal() constant returns (uint winningProposal) {
        uint winningVoteCount = 0;
        for (uint p = 0; p < proposals.length; p++) {
            if (proposals[p].voteCount > winningVoteCount) {
                winningVoteCount = proposals[p].voteCount;
                winningProposal = p;
            }
        }
    }

    function winnerName() constant returns (bytes32 winnerName) {
        winnerName = proposals[winningProposal()].name;
    }
}
"""

def as_byte32(val):
    if isinstance(val, str):
        val = val.encode('utf-8')
    return val + (b'\x00' * (32 - len(val)))

class ContractTest(FaucetMixin, AsyncHandlerTest):

    def get_urls(self):
        return []

    @unittest.skipIf(get_path_of("solc") is None, "couldn't find solc compiler, skipping test")
    @gen_test(timeout=60)
    @requires_parity(pass_parity='node')
    async def test_deploy_contract(self, *, node):

        sourcecode = b"contract greeter{string greeting;function greeter(string _greeting) public{greeting=_greeting;}function greet() constant returns (string){return greeting;}}"
        contract_name = 'greeter'
        constructor_data = [b'hello world!']

        contract = await Contract.from_source_code(sourcecode, contract_name, constructor_data=constructor_data, deployer_private_key=FAUCET_PRIVATE_KEY)

        # call the contract and check the result
        result = await contract.greet()
        self.assertEqual(result, constructor_data[0].decode('utf-8'))

        sourcecode = b"contract adder { function adder() public {} function add(int a, int b) constant returns (int) { return a + b; } }"
        contract_name = 'adder'
        constructor_data = []

        contract = await Contract.from_source_code(sourcecode, contract_name, constructor_data=constructor_data, deployer_private_key=FAUCET_PRIVATE_KEY)

        # call the contract and check the result
        result = await contract.add(1, 2)
        self.assertEqual(result, 3)

    @unittest.skipIf(get_path_of("solc") is None, "couldn't find solc compiler, skipping test")
    @gen_test(timeout=60)
    @requires_parity(pass_parity='node')
    async def test_complex_contract(self, *, node):

        sourcecode = VOTER_CONTRACT_SOURCECODE.encode('utf-8')
        contract_name = 'Ballot'
        proposals = [b'James', b'Frank', b'Bob', b'Dave']
        constructor_data = [proposals]

        contract = await Contract.from_source_code(sourcecode, contract_name, constructor_data=constructor_data, deployer_private_key=FAUCET_PRIVATE_KEY)

        voter1 = ("0xc505998dcc54a5b6424c69b615ef8a7b9ee9881b3a4596dd889ba626c5dd9f9f", "0x0100267048677a95cf91b487d9b65708c105dfe6")
        voter2 = ("0xe17c72f9b49ea9bd7f1690d2b885da0abc5c1cf735306f7ecbcc611e6eb597ef", "0x0200d3013d64c48d1948f0bc8631056df5fc1e7e")
        voter3 = ("0xef50367e453f942827e1b8600424865f05740610e45fb0c320f319e32f757153", "0x030086615f23c951306728d8cc0a9004b47de00b")
        voter4 = ("0xec67294146bbfbfa0d8a2643c7620c24a2fa4a289e123e261fbd6cdc0dc4033b", "0x0400078b1733da5cfd0c48203ae9afdac7f79702")
        voter5 = ("0xba68ad719b30f63ae35118762983602169fe4c5215b7ad7036a6f8c186498897", "0x050011b88ef2a919c49a6d8961744ae9bc658079")

        wei = 10 ** 18

        await self.faucet(voter1[1], wei)
        await self.faucet(voter2[1], wei)
        await self.faucet(voter3[1], wei)
        await self.faucet(voter4[1], wei)
        await self.faucet(voter5[1], wei)

        await contract.giveRightToVote.set_sender(FAUCET_PRIVATE_KEY)(voter1[1])
        await contract.giveRightToVote.set_sender(FAUCET_PRIVATE_KEY)(voter2[1])
        await contract.giveRightToVote.set_sender(FAUCET_PRIVATE_KEY)(voter3[1])
        await contract.giveRightToVote.set_sender(FAUCET_PRIVATE_KEY)(voter4[1])
        await contract.giveRightToVote.set_sender(FAUCET_PRIVATE_KEY)(voter5[1])
        await contract.vote.set_sender(voter1[0])(1)
        await contract.vote.set_sender(voter2[0])(1)
        await contract.delegate.set_sender(voter3[0])(voter4[1])
        await contract.vote.set_sender(voter4[0])(2)
        await contract.vote.set_sender(voter5[0])(2)

        winner = await contract.winnerName()

        self.assertEqual(winner, as_byte32(proposals[2]))

        # ethclient = JsonRPCClient(node.dsn()['url'])
        # bal1 = await ethclient.eth_getBalance(voter1[1])
        # print(bal1)
        # bal2 = await ethclient.eth_getBalance(voter3[1])
        # print(bal2)
