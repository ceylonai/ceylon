use std::collections::{HashMap, HashSet};
use std::fmt::Debug;
use std::future::Future;
use std::pin::Pin;
use std::sync::Arc;
use tokio::sync::Mutex;
use async_trait::async_trait;

#[derive(Debug, Clone, PartialEq)]
pub enum TaskStatus {
    Pending,
    Running,
    Completed,
    Failed(String),
    Skipped,
}

#[derive(Debug, Clone, PartialEq)]
pub enum GraphStatus {
    New,
    Running,
    Completed,
    Failed(String),
}

#[async_trait]
pub trait AsyncTask: Send + Sync + Debug {
    fn id(&self) -> &str;
    fn dependencies(&self) -> &[String] { &[] }
    async fn execute(&self) -> Result<(), String>;
}

#[derive(Debug)]
pub struct TaskNode {
    task: Box<dyn AsyncTask>,
    status: TaskStatus,
}

impl TaskNode {
    pub fn new(task: Box<dyn AsyncTask>) -> Self {
        Self {
            task,
            status: TaskStatus::Pending,
        }
    }
}

pub struct AsyncGraph {
    nodes: HashMap<String, Arc<Mutex<TaskNode>>>,
    dependencies: HashMap<String, Vec<String>>,
    reverse_deps: HashMap<String, Vec<String>>,
    status: GraphStatus,
}

impl AsyncGraph {
    pub fn new() -> Self {
        Self {
            nodes: HashMap::new(),
            dependencies: HashMap::new(),
            reverse_deps: HashMap::new(),
            status: GraphStatus::New,
        }
    }

    pub fn add_task(&mut self, task: Box<dyn AsyncTask>) -> Result<(), String> {
        let task_id = task.id().to_string();
        let deps = task.dependencies().to_vec();

        // Check for cycles
        if self.would_create_cycle(&task_id, &deps) {
            return Err(format!("Adding task {} would create a cycle", task_id));
        }

        // Add dependencies
        self.dependencies.insert(task_id.clone(), deps.clone());
        for dep in deps {
            self.reverse_deps
                .entry(dep)
                .or_default()
                .push(task_id.clone());
        }

        // Add task node
        self.nodes.insert(task_id, Arc::new(Mutex::new(TaskNode::new(task))));
        Ok(())
    }

    pub async fn execute(&mut self) -> Result<(), String> {
        self.status = GraphStatus::Running;

        let mut completed = HashSet::new();

        while completed.len() < self.nodes.len() {
            let ready_tasks = self.get_ready_tasks(&completed);
            if ready_tasks.is_empty() && completed.len() < self.nodes.len() {
                self.status = GraphStatus::Failed("Deadlock detected".to_string());
                return Err("Deadlock detected".to_string());
            }

            let mut handles = Vec::new();

            for task_id in ready_tasks {
                let node = Arc::clone(self.nodes.get(&task_id).unwrap());
                let task_id = task_id.clone();

                handles.push(tokio::spawn(async move {
                    let mut node = node.lock().await;
                    node.status = TaskStatus::Running;

                    match node.task.execute().await {
                        Ok(()) => {
                            node.status = TaskStatus::Completed;
                            Ok(task_id)
                        }
                        Err(e) => {
                            node.status = TaskStatus::Failed(e.clone());
                            Err(e)
                        }
                    }
                }));
            }

            for handle in handles {
                match handle.await {
                    Ok(Ok(task_id)) => {
                        completed.insert(task_id);
                    }
                    Ok(Err(e)) => {
                        self.status = GraphStatus::Failed(e.clone());
                        return Err(e);
                    }
                    Err(e) => {
                        self.status = GraphStatus::Failed(e.to_string());
                        return Err(e.to_string());
                    }
                }
            }
        }

        self.status = GraphStatus::Completed;
        Ok(())
    }

    fn get_ready_tasks(&self, completed: &HashSet<String>) -> Vec<String> {
        self.nodes
            .keys()
            .filter(|task_id| {
                !completed.contains(*task_id) &&
                    self.dependencies
                        .get(*task_id)
                        .map(|deps| deps.iter().all(|dep| completed.contains(dep)))
                        .unwrap_or(true)
            })
            .cloned()
            .collect()
    }

    fn would_create_cycle(&self, new_task: &str, new_deps: &[String]) -> bool {
        let mut dep_map = self.dependencies.clone();
        dep_map.insert(new_task.to_string(), new_deps.to_vec());

        let mut visited = HashSet::new();
        let mut stack = vec![new_task.to_string()];

        while let Some(current) = stack.pop() {
            if !visited.insert(current.clone()) {
                return true;
            }

            if let Some(deps) = dep_map.get(&current) {
                stack.extend(deps.iter().cloned());
            }
        }

        false
    }

    pub fn status(&self) -> &GraphStatus {
        &self.status
    }

    pub async fn get_task_status(&self, task_id: &str) -> Option<TaskStatus> {
        self.nodes.get(task_id).map(|node| {
            node.try_lock()
                .map(|node| node.status.clone())
                .unwrap_or(TaskStatus::Running)
        })
    }
}

// Example implementation
#[cfg(test)]
mod tests {
    use super::*;
    use std::time::Duration;

    #[derive(Debug)]
    struct TestTask {
        id: String,
        deps: Vec<String>,
        delay: Duration,
    }

    #[async_trait]
    impl AsyncTask for TestTask {
        fn id(&self) -> &str {
            &self.id
        }

        fn dependencies(&self) -> &[String] {
            &self.deps
        }

        async fn execute(&self) -> Result<(), String> {
            tokio::time::sleep(self.delay).await;
            Ok(())
        }
    }

    #[tokio::test]
    async fn test_graph_execution() {
        let mut graph = AsyncGraph::new();

        // Add tasks with dependencies
        graph.add_task(Box::new(TestTask {
            id: "task1".to_string(),
            deps: vec![],
            delay: Duration::from_millis(100),
        })).unwrap();

        graph.add_task(Box::new(TestTask {
            id: "task2".to_string(),
            deps: vec!["task1".to_string()],
            delay: Duration::from_millis(50),
        })).unwrap();

        // Execute graph
        graph.execute().await.unwrap();
        assert_eq!(*graph.status(), GraphStatus::Completed);
    }
}