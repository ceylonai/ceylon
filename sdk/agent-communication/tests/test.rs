/*
 *
 *  * Copyright 2024-Present, Syigen Ltd. and Syigen Private Limited. All rights reserved.
 *  * Licensed under the Apache License, Version 2.0 (See LICENSE or http://www.apache.org/licenses/LICENSE-2.0).
 *  *
 *
 */
#[cfg(test)]
mod tests {
    use agent_communication::data::AgentConfig;
    use agent_communication::messaging::{AnpCodec, AnpRequest, AnpResponse};
    use agent_communication::peer::Peer;
    use agent_communication::peer_builder::AgentNodeBuilder;
    use agent_communication::peer_swarm::PeerManager;
    use agent_communication::protocol::anp::AnpMessage;
    use futures::io::Cursor;
    use libp2p::request_response::Codec;
    use libp2p::{identity, Multiaddr, PeerId};
    use serde_json::json;

    // Helper function to create a test AnpMessage
    fn create_test_message(from: &str, to: &str, action: &str) -> AnpMessage {
        let payload = json!({
            "action": action,
            "data": "test data"
        });

        AnpMessage::new(
            from.to_string(),
            to.to_string(),
            payload,
            "test_signature".to_string(),
        )
    }

    #[test]
    fn test_anp_message_creation() {
        let payload = json!({
            "action": "ping",
            "timestamp": 1234567890
        });

        let message = AnpMessage::new(
            "agent1".to_string(),
            "agent2".to_string(),
            payload.clone(),
            "signature123".to_string(),
        );

        assert_eq!(message.version, "1.0");
        assert_eq!(message.msg_type, "request");
        assert_eq!(message.from, "agent1");
        assert_eq!(message.to, "agent2");
        assert_eq!(message.payload, payload);
        assert_eq!(message.signature, "signature123");
        assert!(!message.timestamp.is_empty());
    }

    #[test]
    fn test_anp_message_serialization() {
        let message = create_test_message("agent1", "agent2", "ping");

        // Test serialization
        let serialized = serde_json::to_string(&message).unwrap();
        assert!(serialized.contains("\"version\":\"1.0\""));
        assert!(serialized.contains("\"from\":\"agent1\""));
        assert!(serialized.contains("\"to\":\"agent2\""));

        // Test deserialization
        let deserialized: AnpMessage = serde_json::from_str(&serialized).unwrap();
        assert_eq!(deserialized.from, message.from);
        assert_eq!(deserialized.to, message.to);
        assert_eq!(deserialized.payload, message.payload);
    }

    #[tokio::test]
    async fn test_anp_codec_request_response() {
        let mut codec = AnpCodec::default();
        let protocol = "/anp/1.0.0";

        // Create test message
        let original_msg = create_test_message("sender", "receiver", "executeTask");
        let request = AnpRequest(original_msg.clone());

        // Serialize request
        let mut write_buf = Vec::new();
        {
            let mut cursor = Cursor::new(&mut write_buf);
            codec
                .write_request(&protocol, &mut cursor, request)
                .await
                .unwrap();
        }

        // Deserialize request
        let mut read_cursor = Cursor::new(&write_buf);
        let decoded_request = codec
            .read_request(&protocol, &mut read_cursor)
            .await
            .unwrap();

        assert_eq!(decoded_request.0.from, original_msg.from);
        assert_eq!(decoded_request.0.to, original_msg.to);
        assert_eq!(decoded_request.0.payload, original_msg.payload);
    }

    #[tokio::test]
    async fn test_anp_codec_response() {
        let mut codec = AnpCodec::default();
        let protocol = "/anp/1.0.0";

        // Create test response
        let response_msg = create_test_message("receiver", "sender", "taskComplete");
        let response = AnpResponse(response_msg.clone());

        // Serialize response
        let mut write_buf = Vec::new();
        {
            let mut cursor = Cursor::new(&mut write_buf);
            codec
                .write_response(&protocol, &mut cursor, response)
                .await
                .unwrap();
        }

        // Deserialize response
        let mut read_cursor = Cursor::new(&write_buf);
        let decoded_response = codec
            .read_response(&protocol, &mut read_cursor)
            .await
            .unwrap();

        assert_eq!(decoded_response.0.from, response_msg.from);
        assert_eq!(decoded_response.0.to, response_msg.to);
        assert_eq!(decoded_response.0.payload, response_msg.payload);
    }

    #[tokio::test]
    async fn test_anp_codec_empty_buffer() {
        let mut codec = AnpCodec::default();
        let protocol = "/anp/1.0.0";

        // Test with empty buffer
        let mut empty_cursor = Cursor::new(Vec::<u8>::new());
        let result = codec.read_request(&protocol, &mut empty_cursor).await;

        assert!(result.is_err());
        assert_eq!(
            result.unwrap_err().kind(),
            std::io::ErrorKind::UnexpectedEof
        );
    }

    #[tokio::test]
    async fn test_anp_codec_invalid_json() {
        let mut codec = AnpCodec::default();
        let protocol = "/anp/1.0.0";

        // Test with invalid JSON
        let invalid_json = b"invalid json data";
        let mut cursor = Cursor::new(invalid_json);
        let result = codec.read_request(&protocol, &mut cursor).await;

        assert!(result.is_err());
        assert_eq!(result.unwrap_err().kind(), std::io::ErrorKind::InvalidData);
    }

    #[test]
    fn test_peer_creation() {
        let keypair = identity::Keypair::generate_ed25519();
        let peer_id = PeerId::from(keypair.public());

        let peer = Peer::new(peer_id);

        assert_eq!(peer.id, peer_id);
        assert_eq!(peer.addresses.len(), 0);
        assert!(!peer.connected);
    }

    #[test]
    fn test_peer_address_management() {
        let keypair = identity::Keypair::generate_ed25519();
        let peer_id = PeerId::from(keypair.public());
        let mut peer = Peer::new(peer_id);

        let addr1: Multiaddr = "/ip4/127.0.0.1/tcp/4001".parse().unwrap();
        let addr2: Multiaddr = "/ip4/192.168.1.1/tcp/4002".parse().unwrap();

        // Add addresses
        peer.add_address(addr1.clone());
        peer.add_address(addr2.clone());

        assert_eq!(peer.addresses.len(), 2);
        assert!(peer.addresses.contains(&addr1));
        assert!(peer.addresses.contains(&addr2));

        // Try to add duplicate address
        peer.add_address(addr1.clone());
        assert_eq!(peer.addresses.len(), 2); // Should not increase
    }

    #[test]
    fn test_peer_connection_status() {
        let keypair = identity::Keypair::generate_ed25519();
        let peer_id = PeerId::from(keypair.public());
        let mut peer = Peer::new(peer_id);

        assert!(!peer.connected);

        peer.set_connected(true);
        assert!(peer.connected);

        peer.set_connected(false);
        assert!(!peer.connected);
    }

    #[test]
    fn test_peer_manager() {
        let mut manager = PeerManager::new();

        // Create test peers
        let keypair1 = identity::Keypair::generate_ed25519();
        let peer_id1 = PeerId::from(keypair1.public());
        let peer1 = Peer::new(peer_id1);

        let keypair2 = identity::Keypair::generate_ed25519();
        let peer_id2 = PeerId::from(keypair2.public());
        let peer2 = Peer::new(peer_id2);

        // Test adding peers
        manager.add_peer(peer1);
        manager.add_peer(peer2);

        assert_eq!(manager.count(), 2);
        assert!(manager.get_peer(&peer_id1).is_some());
        assert!(manager.get_peer(&peer_id2).is_some());

        // Test removing peer
        manager.remove_peer(&peer_id1);
        assert_eq!(manager.count(), 1);
        assert!(manager.get_peer(&peer_id1).is_none());
        assert!(manager.get_peer(&peer_id2).is_some());
    }

    #[test]
    fn test_peer_manager_mutation() {
        let mut manager = PeerManager::new();

        let keypair = identity::Keypair::generate_ed25519();
        let peer_id = PeerId::from(keypair.public());
        let peer = Peer::new(peer_id);

        manager.add_peer(peer);

        // Test mutable access
        {
            let peer_mut = manager.get_peer_mut(&peer_id).unwrap();
            peer_mut.set_connected(true);

            let addr: Multiaddr = "/ip4/127.0.0.1/tcp/4001".parse().unwrap();
            peer_mut.add_address(addr);
        }

        let peer = manager.get_peer(&peer_id).unwrap();
        assert!(peer.connected);
        assert_eq!(peer.addresses.len(), 1);
    }

    #[test]
    fn test_peer_manager_iteration() {
        let mut manager = PeerManager::new();

        // Add multiple peers
        for i in 0..5 {
            let keypair = identity::Keypair::generate_ed25519();
            let peer_id = PeerId::from(keypair.public());
            let peer = Peer::new(peer_id);
            manager.add_peer(peer);
        }

        assert_eq!(manager.count(), 5);

        let collected_peers: Vec<_> = manager.all_peers().collect();
        assert_eq!(collected_peers.len(), 5);
    }

    #[test]
    fn test_agent_config_creation() {
        let addr1: Multiaddr = "/ip4/127.0.0.1/tcp/4001".parse().unwrap();
        let addr2: Multiaddr = "/ip4/0.0.0.0/tcp/4002".parse().unwrap();
        let addrs = vec![addr1, addr2];

        let config = AgentConfig::new(None, addrs.clone(), "/anp/1.0.0");

        assert_eq!(config.protocol, "/anp/1.0.0");
        assert_eq!(config.listen_addrs, addrs);
        assert_eq!(config.request_timeout_secs, 10);
        assert_eq!(config.keep_alive_secs, 60);
        assert!(config.keypair.is_some());
    }

    #[test]
    fn test_agent_config_with_custom_keypair() {
        let keypair = identity::Keypair::generate_ed25519();
        let expected_peer_id = PeerId::from(keypair.public());

        let config = AgentConfig::new(Some(keypair), vec![], "/anp/1.0.0");

        assert_eq!(config.peer_id, expected_peer_id);
    }

    #[test]
    fn test_agent_config_customization() {
        let config = AgentConfig::new(None, vec![], "/anp/1.0.0")
            .with_request_timeout_secs(30)
            .with_keep_alive_secs(120);

        assert_eq!(config.request_timeout_secs, 30);
        assert_eq!(config.keep_alive_secs, 120);
    }

    #[test]
    fn test_agent_config_serialization() {
        let addr: Multiaddr = "/ip4/127.0.0.1/tcp/4001".parse().unwrap();
        let config = AgentConfig::new(None, vec![addr], "/anp/1.0.0");

        let serialized = serde_json::to_string(&config).unwrap();

        assert!(serialized.contains("\"protocol\":\"/anp/1.0.0\""));
        assert!(serialized.contains("\"request_timeout_secs\":10"));
        assert!(serialized.contains("\"keep_alive_secs\":60"));
        assert!(serialized.contains("\"keypair\":\"--\""));
    }

    #[test]
    fn test_agent_node_builder() {
        let builder = AgentNodeBuilder::new()
            .with_listen_addr("/ip4/127.0.0.1/tcp/4001")
            .with_listen_addr("/ip4/0.0.0.0/tcp/4002")
            .with_protocol("/anp/2.0.0");

        let config = builder.build();

        assert_eq!(config.protocol, "/anp/2.0.0");
        assert_eq!(config.listen_addrs.len(), 2);
        assert_eq!(config.request_timeout_secs, 10);
        assert_eq!(config.keep_alive_secs, 60);
    }

    #[test]
    fn test_agent_node_builder_with_keypair() {
        let keypair = identity::Keypair::generate_ed25519();
        let expected_peer_id = PeerId::from(keypair.public());

        let config = AgentNodeBuilder::new().with_keypair(keypair).build();

        assert_eq!(config.peer_id, expected_peer_id);
    }

    #[test]
    fn test_agent_node_builder_default_protocol() {
        let config = AgentNodeBuilder::new().build();
        assert_eq!(config.protocol, "/anp/1.0.0");
    }

    #[test]
    fn test_anp_request_display() {
        let message = create_test_message("agent1", "agent2", "ping");
        let request = AnpRequest(message);

        let display_str = format!("{}", request);
        assert!(display_str.contains("AnpRequest"));
        assert!(display_str.contains("agent1"));
        assert!(display_str.contains("agent2"));
        assert!(display_str.contains("request"));
    }

    #[test]
    fn test_anp_response_display() {
        let message = create_test_message("agent2", "agent1", "pong");
        let response = AnpResponse(message);

        let display_str = format!("{}", response);
        assert!(display_str.contains("AnpResponse"));
        assert!(display_str.contains("agent2"));
        assert!(display_str.contains("agent1"));
        assert!(display_str.contains("request"));
    }

    #[test]
    fn test_message_payload_variations() {
        // Test with different payload types
        let payloads = vec![
            json!({"action": "ping"}),
            json!({"action": "executeTask", "task_id": 123, "params": ["a", "b"]}),
            json!({"action": "response", "data": {"result": "success"}}),
            json!(null),
            json!("simple string"),
            json!(42),
        ];

        for payload in payloads {
            let message = AnpMessage::new(
                "sender".to_string(),
                "receiver".to_string(),
                payload.clone(),
                "sig".to_string(),
            );

            assert_eq!(message.payload, payload);

            // Test serialization roundtrip
            let serialized = serde_json::to_string(&message).unwrap();
            let deserialized: AnpMessage = serde_json::from_str(&serialized).unwrap();
            assert_eq!(deserialized.payload, payload);
        }
    }

    #[test]
    fn test_concurrent_peer_operations() {
        use std::sync::{Arc, Mutex};
        use std::thread;

        let manager = Arc::new(Mutex::new(PeerManager::new()));
        let mut handles = vec![];

        // Spawn multiple threads to add peers concurrently
        for i in 0..10 {
            let manager_clone = Arc::clone(&manager);
            let handle = thread::spawn(move || {
                let keypair = identity::Keypair::generate_ed25519();
                let peer_id = PeerId::from(keypair.public());
                let peer = Peer::new(peer_id);

                let mut manager = manager_clone.lock().unwrap();
                manager.add_peer(peer);
            });
            handles.push(handle);
        }

        // Wait for all threads to complete
        for handle in handles {
            handle.join().unwrap();
        }

        let manager = manager.lock().unwrap();
        assert_eq!(manager.count(), 10);
    }

    #[test]
    fn test_protocol_constant() {
        use agent_communication::messaging::ANP_PROTOCOL;
        assert_eq!(ANP_PROTOCOL, "/anp/1.0.0");
    }

    // Integration test for the complete message flow
    #[tokio::test]
    async fn test_complete_message_flow() {
        let mut codec = AnpCodec::default();
        let protocol = "/anp/1.0.0";

        // Create a request message
        let request_msg = create_test_message("client", "server", "executeTask");
        let request = AnpRequest(request_msg.clone());

        // Serialize and deserialize request
        let mut buf = Vec::new();
        {
            let mut cursor = Cursor::new(&mut buf);
            codec
                .write_request(&protocol, &mut cursor, request)
                .await
                .unwrap();
        }

        let mut cursor = Cursor::new(&buf);
        let decoded_request = codec.read_request(&protocol, &mut cursor).await.unwrap();

        // Verify request
        assert_eq!(decoded_request.0.from, "client");
        assert_eq!(decoded_request.0.to, "server");
        assert_eq!(decoded_request.0.payload["action"], "executeTask");

        // Create response message
        let response_msg = create_test_message("server", "client", "taskComplete");
        let response = AnpResponse(response_msg.clone());

        // Serialize and deserialize response
        let mut response_buf = Vec::new();
        {
            let mut cursor = Cursor::new(&mut response_buf);
            codec
                .write_response(&protocol, &mut cursor, response)
                .await
                .unwrap();
        }

        let mut cursor = Cursor::new(&response_buf);
        let decoded_response = codec.read_response(&protocol, &mut cursor).await.unwrap();

        // Verify response
        assert_eq!(decoded_response.0.from, "server");
        assert_eq!(decoded_response.0.to, "client");
        assert_eq!(decoded_response.0.payload["action"], "taskComplete");
    }
}
