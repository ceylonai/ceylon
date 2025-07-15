/*
 *
 *  * Copyright 2024-Present, Syigen Ltd. and Syigen Private Limited. All rights reserved.
 *  * Licensed under the Apache License, Version 2.0 (See LICENSE or http://www.apache.org/licenses/LICENSE-2.0).
 *  *
 *
 */

use crate::protocol::anp::AnpMessage;

pub async fn handle_message(anp: AnpMessage) {
    match anp.payload.get("action").and_then(|v| v.as_str()) {
        Some("executeTask") => {
            println!("Executing task: {:?}", anp.payload);
            // Call your Agent Core logic here
        }
        Some("ping") => {
            println!("Received ping from {}", anp.from);
            // Ping responses help keep connections alive
        }
        Some("heartbeat") => {
            println!("Received heartbeat from {}", anp.from);
            // Heartbeats indicate peer is still active
        }
        Some("chat_message") => {
            // Handle chat messages properly
            if let Some(message) = anp.payload.get("message").and_then(|v| v.as_str()) {
                if let Some(sender) = anp.payload.get("sender").and_then(|v| v.as_str()) {
                    println!("Chat message from {}: {}", sender, message);
                }
            }
        }
        Some("private_message") => {
            // Handle private messages
            if let Some(message) = anp.payload.get("message").and_then(|v| v.as_str()) {
                if let Some(sender) = anp.payload.get("sender").and_then(|v| v.as_str()) {
                    println!("Private message from {}: {}", sender, message);
                }
            }
        }
        Some("ack") => {
            // Acknowledgment received - connection is working
            println!("Received acknowledgment from {}", anp.from);
        }
        _ => {
            println!("Unknown action: {:?}", anp.payload);
        }
    }
}
