use serde::Deserialize;

#[derive(Deserialize, Debug)]
pub struct AgentConfig {
    pub storage_path: String,
    pub communication_endpoint: String,
    pub max_concurrent_tasks: usize,
}

#[derive(Debug)]
pub enum ConfigError {
    DeserializeError(serde_json::Error),
}

impl AgentConfig {
    pub fn load_from_file(path: &str) -> Result<Self, ConfigError> {
        todo!()
    }
}
