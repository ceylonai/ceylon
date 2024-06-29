use tokio::sync::RwLock;
use crate::peer::P2P;

mod blockchain;
mod peer;

#[tokio::main]
async fn main() {
    tokio::spawn(async move {
        let mut p2p = P2P::new().await;
        p2p.connect("/ip4/0.0.0.0/udp/0/quic-v1", "test_topic");
        p2p.run().await;
    }).await.unwrap();


    // let blockchain1 = Mutex::new(Blockchain::new(4));
    // let interval = Duration::from_secs(10);
    // 
    // tokio::spawn(async move {
    //     loop {
    //         let mut blockchain = blockchain1.lock().await;
    //         blockchain.add_block("Some new data".to_string().into_bytes());
    //         println!("Mined a new block: {:?}", blockchain.get_last());
    //         println!("Blockchain valid: {}", blockchain.is_valid());
    // 
    //         sleep(interval).await;
    //     }
    // }).await.unwrap();
}
