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
        }
        _ => {
            println!("Unknown action: {:?}", anp.payload);
        }
    }
}
