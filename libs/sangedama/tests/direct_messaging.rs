#[cfg(test)]
mod tests {
    use super::*;
    use std::time::Duration;
    use tokio::sync::mpsc;
    use tokio::time::sleep;
    use tokio_util::sync::CancellationToken;
    use sangedama::peer::message::data::{MessageType, NodeMessage};
    use sangedama::peer::node::{create_key, get_peer_id, AdminPeer, AdminPeerConfig, MemberPeer, MemberPeerConfig};

    #[tokio::test]
    async fn test_direct_messaging() {
        // Initialize logging
        let _ = tracing_subscriber::fmt()
            .with_env_filter("info")
            .try_init();

        // Create cancellation token
        let cancel_token = CancellationToken::new();

        // Setup admin node for discovery
        let admin_config = AdminPeerConfig::new(7845, "test-workspace".to_string());
        let admin_key = create_key();
        let admin_id = get_peer_id(&admin_key).to_string();

        let (mut admin_peer, _) = AdminPeer::create(admin_config, admin_key).await;

        let admin_task = tokio::spawn({
            let cancel_token = cancel_token.clone();
            async move {
                admin_peer.run(None, cancel_token).await;
            }
        });

        // Wait for admin to start
        sleep(Duration::from_secs(1)).await;

        // Create two member peers
        let member1_config = MemberPeerConfig::new(
            "peer1".to_string(),
            "test-workspace".to_string(),
            admin_id.clone(),
            7845,
            "127.0.0.1".to_string(),
        );

        let member2_config = MemberPeerConfig::new(
            "peer2".to_string(),
            "test-workspace".to_string(),
            admin_id.clone(),
            7845,
            "127.0.0.1".to_string(),
        );

        let (mut member1, mut member1_rx) = MemberPeer::create(member1_config, create_key()).await;
        let (mut member2, mut member2_rx) = MemberPeer::create(member2_config, create_key()).await;

        let member1_id = member1.id.clone();
        let member2_id = member2.id.clone();

        // Get message senders
        let member1_sender = member1.get_sender();
        let member2_sender = member2.get_sender();

        // Start the peers
        let member1_task = tokio::spawn({
            let cancel_token = cancel_token.clone();
            async move {
                member1.run(cancel_token).await;
            }
        });

        let member2_task = tokio::spawn({
            let cancel_token = cancel_token.clone();
            async move {
                member2.run(cancel_token).await;
            }
        });

        // Wait for peers to connect
        sleep(Duration::from_secs(2)).await;

        // Create channel for test results
        let (test_tx, mut test_rx) = mpsc::channel::<String>(10);

        // Setup message listeners
        let member1_listener = tokio::spawn({
            let tx = test_tx.clone();
            async move {
                while let Some(msg) = member1_rx.recv().await {
                    if let NodeMessage::Message { data, .. } = msg {
                        let msg_str = String::from_utf8(data).unwrap();
                        tx.send(format!("peer1 received: {}", msg_str)).await.unwrap();
                    }
                }
            }
        });

        let member2_listener = tokio::spawn({
            let tx = test_tx;
            async move {
                while let Some(msg) = member2_rx.recv().await {
                    if let NodeMessage::Message { data, .. } = msg {
                        let msg_str = String::from_utf8(data).unwrap();
                        tx.send(format!("peer2 received: {}", msg_str)).await.unwrap();
                    }
                }
            }
        });

        // Send test messages
        member1_sender
            .send("Hello from peer1".as_bytes().to_vec())
            .await
            .unwrap();

        member2_sender
            .send("Hello from peer2".as_bytes().to_vec())
            .await
            .unwrap();

        // Collect messages
        let mut received_messages = Vec::new();
        for _ in 0..2 {
            if let Ok(msg) = tokio::time::timeout(Duration::from_secs(5), test_rx.recv()).await {
                if let Some(message) = msg {
                    received_messages.push(message);
                }
            }
        }

        // Cleanup
        cancel_token.cancel();

        // Verify messages
        assert_eq!(received_messages.len(), 2);
        assert!(received_messages.iter().any(|msg| msg.contains("peer1 received:")));
        assert!(received_messages.iter().any(|msg| msg.contains("peer2 received:")));

        // Wait for tasks to complete
        let _ = tokio::join!(admin_task, member1_task, member2_task, member1_listener, member2_listener);
    }
}