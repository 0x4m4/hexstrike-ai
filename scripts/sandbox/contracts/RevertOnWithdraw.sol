// SPDX-License-Identifier: MIT
pragma solidity ^0.8.19;

/// @notice HoneyPot: withdraw reverts when contract balance differs from snapshot.
contract RevertOnWithdraw {
    uint256 private snapshotBalance;
    bool private snapshotted;

    receive() external payable {}

    function snapshot() external {
        snapshotBalance = address(this).balance;
        snapshotted = true;
    }

    function withdraw(address payable to, uint256 amount) external {
        if (!snapshotted) {
            snapshotBalance = address(this).balance;
            snapshotted = true;
        }
        if (address(this).balance != snapshotBalance) {
            revert("BLOCK");
        }
        require(address(this).balance >= amount, "insufficient");
        (bool ok, ) = to.call{value: amount}("");
        require(ok, "transfer failed");
    }
}
