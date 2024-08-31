use std::collections::HashMap;
use std::fs::OpenOptions;
use std::io::Write;
pub(crate) fn write_to_env_file(env_vars: &HashMap<String, String>) -> std::io::Result<()> {
    let mut file = OpenOptions::new()
        .create(true)
        .append(true)
        .open(".ceylon_network")?;

    for (key, value) in env_vars {
        writeln!(file, "{}={}", key, value)?;
    }

    Ok(())
}