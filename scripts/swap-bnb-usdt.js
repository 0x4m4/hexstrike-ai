#!/usr/bin/env node
/**
 * Swap BNB → USDT on BSC via PancakeSwap V2 (operator lab).
 * Usage:
 *   CONFIRM=yes node ~/swap-bnb-usdt.js
 *   BNB_AMOUNT=0.005 CONFIRM=yes node ~/swap-bnb-usdt.js
 */
const fs = require('fs');
const path = require('path');

// ethers in ~/node_modules (operator-signing package.json)
const homeModules = path.join(process.env.HOME || '', 'node_modules');
if (homeModules) module.paths.unshift(homeModules);

const { ethers } = require('ethers');

const OPERATOR = process.env.FROM || '0x85dB346BE1d9d5D8ec4F57acf0067FbE53a6E846';
const RPC = process.env.BSC_RPC || 'https://bsc-dataseed.binance.org/';
const ROUTER = ethers.getAddress('0x10ED43C718714eb63d5aB7E8d58b0B6B0a0b54852');
const WBNB = ethers.getAddress('0xbb4cdb9cbd36b01bd1cbaebf2de08d91793bc95c');
const USDT = ethers.getAddress('0x55d398326f99059fF775485246999027B3197955');
const KEY_PATH = process.env.PROOF_KEY || path.join(process.env.HOME, 'proof-key.txt');
const BNB_AMOUNT = process.env.BNB_AMOUNT || '0.005';

const ROUTER_ABI = [
  'function getAmountsOut(uint amountIn, address[] calldata path) view returns (uint[] memory amounts)',
  'function swapExactETHForTokens(uint amountOutMin, address[] calldata path, address to, uint deadline) payable returns (uint[] memory amounts)',
];
const ERC20_ABI = ['function balanceOf(address) view returns (uint256)'];

async function main() {
  if (process.env.CONFIRM !== 'yes') {
    console.log('PREVIEW — add CONFIRM=yes to swap');
    console.log('BNB amount:', BNB_AMOUNT);
    console.log('Key:', KEY_PATH);
    process.exit(0);
  }

  let key = fs.readFileSync(KEY_PATH, 'utf8').trim();
  if (!key.startsWith('0x')) key = '0x' + key;

  const provider = new ethers.JsonRpcProvider(RPC);
  const wallet = new ethers.Wallet(key, provider);
  const router = new ethers.Contract(ROUTER, ROUTER_ABI, wallet);
  const usdt = new ethers.Contract(USDT, ERC20_ABI, provider);

  const value = ethers.parseEther(BNB_AMOUNT);
  const pathAddrs = [WBNB, USDT];
  const amounts = await router.getAmountsOut(value, pathAddrs);
  const expectedUsdt = amounts[1];
  const minOut = (expectedUsdt * 95n) / 100n; // 5% slippage
  const deadline = Math.floor(Date.now() / 1000) + 600;

  const bnbBefore = await provider.getBalance(wallet.address);
  const usdtBefore = await usdt.balanceOf(wallet.address);

  console.log('From:', wallet.address);
  console.log('Swap:', BNB_AMOUNT, 'BNB → ~', ethers.formatUnits(expectedUsdt, 18), 'USDT');
  console.log('Sending tx...');

  const tx = await router.swapExactETHForTokens(minOut, pathAddrs, wallet.address, deadline, {
    value,
    gasLimit: 250000n,
  });
  console.log('TX:', tx.hash);
  const receipt = await tx.wait();
  console.log('Status:', receipt.status === 1 ? 'success' : 'failed');

  const usdtAfter = await usdt.balanceOf(wallet.address);
  const bnbAfter = await provider.getBalance(wallet.address);

  console.log('BNB before/after:', ethers.formatEther(bnbBefore), '→', ethers.formatEther(bnbAfter));
  console.log('USDT before/after:', ethers.formatUnits(usdtBefore, 18), '→', ethers.formatUnits(usdtAfter, 18));
  console.log('Explorer: https://bscscan.com/tx/' + tx.hash);
}

main().catch((e) => {
  console.error('Error:', e.message);
  process.exit(1);
});
