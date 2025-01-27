use std::collections::{HashMap, HashSet};
use std::sync::{Arc, Mutex};

#[derive(Debug, Clone, PartialEq)]
pub enum TaskState {
    Ready,
    Running,
    Complete,
    Failed(String),
    Skipped,
}

#[derive(Debug, Clone, PartialEq)]
pub enum WorkflowState {
    New,
    Running,
    Complete,
    Failed(String),
}

pub trait Task: Send + Sync {
    fn id(&self) -> &str;
    fn run(&mut self) -> Result<(), String>;
    fn state(&self) -> &TaskState;
    fn set_state(&mut self, state: TaskState);
    fn dependencies(&self) -> &[String] {
        &[]
    }
}

#[derive(Default)]
struct DependencyGraph {
    dependencies: HashMap<String, Vec<String>>,
    reverse_dependencies: HashMap<String, Vec<String>>,
}

impl DependencyGraph {
    fn new() -> Self {
        Self::default()
    }

    fn add_task(&mut self, task_id: String, dependencies: &[String]) {
        self.dependencies
            .insert(task_id.clone(), dependencies.to_vec());
        for dep in dependencies {
            self.reverse_dependencies
                .entry(dep.clone())
                .or_default()
                .push(task_id.clone());
        }
    }

    fn get_tasks_with_no_dependencies(&self) -> Vec<String> {
        self.dependencies
            .iter()
            .filter(|(_, deps)| deps.is_empty())
            .map(|(task_id, _)| task_id.clone())
            .collect()
    }

    fn remove_task(&mut self, task_id: &str) {
        self.dependencies.remove(task_id);
        for deps in self.dependencies.values_mut() {
            deps.retain(|dep| dep != task_id);
        }
        self.reverse_dependencies.remove(task_id);
    }
}

pub struct ParallelWorkflow {
    id: String,
    state: WorkflowState,
    tasks: HashMap<String, Arc<Mutex<Box<dyn Task>>>>,
    completed: HashSet<String>,
    dependency_graph: DependencyGraph,
}

impl ParallelWorkflow {
    pub fn new(id: String) -> Self {
        ParallelWorkflow {
            id,
            state: WorkflowState::New,
            tasks: HashMap::new(),
            completed: HashSet::new(),
            dependency_graph: DependencyGraph::new(),
        }
    }

    pub fn add_task(&mut self, task: Box<dyn Task>) -> Result<(), String> {
        let task_id = task.id().to_string();
        let dependencies = task.dependencies().to_vec();

        if self.would_create_cycle(&task_id, &dependencies) {
            return Err(format!(
                "Adding task {} would create a dependency cycle",
                task_id
            ));
        }

        self.dependency_graph
            .add_task(task_id.clone(), &dependencies);
        self.tasks.insert(task_id, Arc::new(Mutex::new(task)));
        Ok(())
    }

    pub fn is_empty(&self) -> bool {
        self.tasks.is_empty()
    }

    pub fn get_task(&self, task_id: &str) -> Option<&Arc<Mutex<Box<dyn Task>>>> {
        self.tasks.get(task_id)
    }

    pub fn get_tasks_with_no_dependencies(&self) -> Vec<String> {
        self.dependency_graph.get_tasks_with_no_dependencies()
    }

    pub fn mark_completed(&mut self, task_id: String) {
        self.completed.insert(task_id);
    }

    pub fn set_state(&mut self, state: WorkflowState) {
        self.state = state;
    }

    pub fn state(&self) -> &WorkflowState {
        &self.state
    }

    pub fn cleanup_completed_tasks(&mut self) {
        for completed_task in &self.completed {
            self.dependency_graph.remove_task(completed_task);
            self.tasks.remove(completed_task);
        }
        self.completed.clear();
    }

    pub fn validate(&self) -> Result<(), String> {
        for (id, task) in &self.tasks {
            for dep in task.lock().unwrap().dependencies() {
                if !self.tasks.contains_key(dep) {
                    return Err(format!("Task {} depends on missing task {}", id, dep));
                }
            }
        }
        Ok(())
    }

    fn would_create_cycle(&self, new_task: &str, new_deps: &[String]) -> bool {
        let mut dep_map: HashMap<String, Vec<String>> = self
            .tasks
            .iter()
            .map(|(id, task)| (id.clone(), task.lock().unwrap().dependencies().to_vec()))
            .collect();

        dep_map.insert(new_task.to_string(), new_deps.to_vec());

        for start_task in dep_map.keys() {
            let mut visited = HashSet::new();
            let mut stack = vec![start_task.clone()];

            while let Some(current) = stack.pop() {
                if !visited.insert(current.clone()) {
                    if current == *start_task {
                        return true;
                    }
                    continue;
                }

                if let Some(deps) = dep_map.get(&current) {
                    stack.extend(deps.iter().cloned());
                }
            }
        }
        false
    }
}

