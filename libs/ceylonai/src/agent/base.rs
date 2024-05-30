use crate::agent::Task;

pub struct BaseAgent<Tt, Rt> {
    pub name: String,
    pub role: String,
    task: Box<dyn Task<Tt, Rt> + Send + Sync>,
}

impl<Tt: Send + Sync, Rt: Send + Sync> BaseAgent<Tt, Rt> {
    pub fn new(name: String, role: String, task: Box<dyn Task<Tt, Rt> + Send + Sync>) -> Self {
        Self {
            name,
            role,
            task,
        }
    }

    pub async fn execute_task(&self, input: Tt) -> Result<Rt, Box<dyn std::error::Error>> {
        let result = self.task.execute(input).await;
        Ok(result)
    }
}