mod peers;


#[tokio::main]
async fn main() {
    peers::peer::create_peer().await;
}
