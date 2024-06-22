// src/lib.rs
use std::time::{SystemTime, UNIX_EPOCH};
use serde::{Serialize, Deserialize};

#[derive(Clone, Debug, Serialize, Deserialize)]
pub struct Transaction {
    data: Vec<u8>,
}

#[derive(Clone, Debug, Serialize, Deserialize)]
pub struct Block {
    index: u64,
    timestamp: u128,
    previous_hash: String,
    hash: String,
    transaction: Transaction,
}

#[derive(Clone, Debug, Serialize, Deserialize)]
pub struct Blockchain {
    blocks: Vec<Block>,
}

impl Blockchain {
    pub fn new() -> Blockchain {
        let mut blockchain = Blockchain { blocks: vec![] };
        blockchain.add_block(Transaction { data: String::from("Genesis Block").as_bytes().to_vec() }, "0".to_string());
        blockchain
    }

    pub fn add_block(&mut self, transaction: Transaction, previous_hash: String) {
        let block = Block {
            index: self.blocks.len() as u64,
            timestamp: SystemTime::now().duration_since(UNIX_EPOCH).unwrap().as_millis(),
            previous_hash,
            hash: String::new(), // Placeholder
            transaction,
        };
        let block = Block {
            hash: self.calculate_hash(&block),
            ..block
        };
        self.blocks.push(block);
    }

    pub fn calculate_hash(&self, block: &Block) -> String {
        let block_data = format!(
            "{}{}{}{:?}",
            block.index, block.timestamp, block.previous_hash, block.transaction.data
        );
        format!("{:x}", md5::compute(block_data))
    }

    pub fn latest_block(&self) -> &Block {
        self.blocks.last().unwrap()
    }
}

#[cfg(test)]
mod tests {
    use std::sync::Arc;
    use super::*;
    use tokio::sync::{mpsc, Mutex};
    use tokio::task;

    pub async fn start_server(mut blockchain: Arc<Mutex<Blockchain>>, mut receiver: mpsc::Receiver<()>, sender: mpsc::Sender<Blockchain>) {
        while let Some(_) = receiver.recv().await {
            let blockchain = blockchain.lock().await;
            sender.send(blockchain.clone()).await.unwrap();
        }
    }

    pub async fn sync_blockchain(sender: mpsc::Sender<()>, mut receiver: mpsc::Receiver<Blockchain>) -> Blockchain {
        sender.send(()).await.unwrap();
        receiver.recv().await.unwrap()
    }

    #[tokio::test]
    async fn test_blockchain_sync() {
        let (server_tx, server_rx) = mpsc::channel(1);
        let (client_tx, client_rx) = mpsc::channel(1);

        let blockchain = Arc::new(Mutex::new(Blockchain::new()));

        let server_handle = task::spawn({
            let blockchain = Arc::clone(&blockchain);
            async move {
                start_server(blockchain, server_rx, client_tx).await;
            }
        });

        // Give the server a moment to start
        tokio::time::sleep(tokio::time::Duration::from_millis(100)).await;

        // Run the client to sync the blockchain
        let client_blockchain = sync_blockchain(server_tx, client_rx).await;

        // Verify the blockchain has been synced correctly
        assert_eq!(client_blockchain.blocks.len(), 1);
        assert_eq!(client_blockchain.blocks[0].transaction.data, "Genesis Block".as_bytes().to_vec());

        // Shut down the server
        server_handle.abort();
    }
}

