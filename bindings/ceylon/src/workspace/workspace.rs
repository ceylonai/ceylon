use tracing::info;

pub struct WorkSpaceConfig {
    pub name: String,
    pub port: u16,
}
pub struct WorkSpace {
    pub config: WorkSpaceConfig,
}

impl WorkSpace {
    pub fn new(config: WorkSpaceConfig) -> WorkSpace {
        WorkSpace { config }
    }

    pub async fn run(&self, _: Vec<u8>) {
        info!("Workspace {} running", self.config.name);
    }
}
