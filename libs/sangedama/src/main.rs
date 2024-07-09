use tracing::{info};
use crate::peer::peer::Peer;

mod p2p;
mod peer;
#[tokio::main]
async fn main() {
    let subscriber = tracing_subscriber::FmtSubscriber::new();
    // use that subscriber to process traces emitted after this point
    tracing::subscriber::set_global_default(subscriber).unwrap();
    info!("Starting sangedama");

    let mut peer = Peer::create().await;
    peer.run().await;
}