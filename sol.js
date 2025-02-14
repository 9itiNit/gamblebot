const express = require('express');
const app = express();
const port = 3000;
const solanaWeb3 = require('@solana/web3.js');
const fs = require('fs');

app.use(express.json());

// Sample wallet generation function
function generateWallet() {
  const keypair = solanaWeb3.Keypair.generate();

// Get the public and private keys
const publicKey = keypair.publicKey.toString();
const privateKey = JSON.stringify(Array.from(keypair.secretKey));

// Save the wallet keys to a file (optional)
fs.writeFileSync('solana_wallet.json', JSON.stringify({
    publicKey: publicKey,
    privateKey: privateKey
}));

console.log('Solana wallet created!');
console.log('Public Key:', publicKey);
console.log('Private Key saved to solana_wallet.json');
  return publicKey;
}
// const connection = new solanaWeb3.Connection('https://api.mainnet-beta.solana.com', 'confirmed');
// const connection = new solanaWeb3.Connection('https://api.testnet.solana.com', 'confirmed')
const connection = new solanaWeb3.Connection('https://api.devnet.solana.com', 'confirmed'); 
// async function getBalance(publicKey) {
//   try {
//       const balance = await connection.getBalance(publicKey);
//       console.log(`Balance for wallet ${publicKey.toString()}: ${balance / solanaWeb3.LAMPORTS_PER_SOL} SOL`);
//   } catch (error) {
//       console.error('Error fetching balance:', error);
//   }
// }

async function getBalance(walletAddress) {
  try {
    // Convert the wallet address to a Solana PublicKey object
    // const publicKey = new solanaWeb3.PublicKey(walletAddress);
    
    // Get the balance for the given wallet address
    const balance = await connection.getBalance(walletAddress);
    
    // Return the balance in SOL (convert from Lamports)
    return balance / solanaWeb3.LAMPORTS_PER_SOL;
  } catch (error) {
    console.error('Error fetching balance:', error);
    throw new Error('Error fetching balance');
  }
}

app.post('/generate-wallet', (req, res) => {
  const walletAddress = generateWallet();
  res.json({ walletAddress: walletAddress });
});

app.post('/get-balance', async (req, res) => {
  const { walletAddress } = req.body; // Expecting wallet address in the request body
  if (!walletAddress) {
      return res.status(400).json({ error: 'Wallet address is required' });
  }

  try {
      const solBalance = getBalance(walletAddress);
      res.json({ balance: solBalance });
  } catch (error) {
      console.error('Error fetching balance:', error);
      res.status(500).json({ error: 'Failed to fetch balance' });
  }
});

app.listen(port, () => {
  console.log(`Server running on http://localhost:${port}`);
});
