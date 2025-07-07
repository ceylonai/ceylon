use thiserror::Error;

#[derive(Error, Debug)]
pub enum CoreError {
    #[error("Lifecycle error: {0}")]
    LifecycleError(String),

    #[error("Task execution error: {0}")]
    TaskError(String),

    #[error("Configuration error: {0}")]
    ConfigError(String),
}
