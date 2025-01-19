/*
 * Copyright 2024-Present, Syigen Ltd. and Syigen Private Limited. All rights reserved.
 * Licensed under the Apache License, Version 2.0 (See LICENSE or http://www.apache.org/licenses/LICENSE-2.0).
 *
 */

use std::collections::HashMap;
use std::fs::File;
use std::io::Write;
pub(crate) fn write_to_env_file(env_vars: &HashMap<&str, String>) -> std::io::Result<()> {
    let mut file = File::create(".ceylon_network")?;

    for (key, value) in env_vars {
        writeln!(file, "{}={}", key, value)?;
    }

    Ok(())
}