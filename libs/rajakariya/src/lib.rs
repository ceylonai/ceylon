use std::collections::{HashMap, HashSet, VecDeque};
use std::sync::{Arc, Mutex};
use std::thread;

// Keeping the same enums from original code
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

// Modified Task trait to be Send + Sync for parallel execution
pub trait Task: Send + Sync {
    fn id(&self) -> &str;
    fn run(&mut self) -> Result<(), String>;
    fn state(&self) -> &TaskState;
    fn set_state(&mut self, state: TaskState);
    fn dependencies(&self) -> &[String] { &[] }
}

// Structure to represent dependency graph
#[derive(Default)]
struct DependencyGraph {
    // Maps task ID to its dependencies
    dependencies: HashMap<String, Vec<String>>,
    // Maps task ID to tasks that depend on it
    reverse_dependencies: HashMap<String, Vec<String>>,
}

impl DependencyGraph {
    fn new() -> Self {
        Self::default()
    }

    fn add_task(&mut self, task_id: String, dependencies: &[String]) {
        self.dependencies.insert(task_id.clone(), dependencies.to_vec());

        // Update reverse dependencies
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
        // Remove the task from dependencies
        self.dependencies.remove(task_id);

        // Remove task from others' dependencies
        for deps in self.dependencies.values_mut() {
            deps.retain(|dep| dep != task_id);
        }

        // Remove from reverse dependencies
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

        // Check for cycles before adding
        if self.would_create_cycle(&task_id, &dependencies) {
            return Err(format!("Adding task {} would create a dependency cycle", task_id));
        }

        // Add to dependency graph
        self.dependency_graph.add_task(task_id.clone(), &dependencies);

        // Add task to tasks map
        self.tasks.insert(task_id, Arc::new(Mutex::new(task)));

        Ok(())
    }

    // Main run method that orchestrates parallel execution
    pub fn run(&mut self) -> Result<(), String> {
        self.validate()?;
        self.state = WorkflowState::Running;

        while !self.tasks.is_empty() {
            // Step 1: Get available tasks
            let available_tasks = self.get_available_tasks();

            if available_tasks.is_empty() && !self.tasks.is_empty() {
                self.state = WorkflowState::Failed("Deadlock detected".to_string());
                return Err("Workflow deadlocked".to_string());
            }

            // Step 2: Execute available tasks in parallel
            let results = self.execute_parallel_tasks(available_tasks)?;

            // Step 3: Process results and update state
            self.process_task_results(results)?;

            // Step 4: Clean up completed tasks
            self.cleanup_completed_tasks();
        }

        self.state = WorkflowState::Complete;
        Ok(())
    }

    fn get_available_tasks(&self) -> Vec<String> {
        self.dependency_graph
            .get_tasks_with_no_dependencies()
            .into_iter()
            .filter(|task_id| {
                if let Some(task) = self.tasks.get(task_id) {
                    matches!(task.lock().unwrap().state(), TaskState::Ready)
                } else {
                    false
                }
            })
            .collect()
    }

    fn execute_parallel_tasks(&self, task_ids: Vec<String>) -> Result<Vec<(String, Result<(), String>)>, String> {
        let mut handles = vec![];
        let results = Arc::new(Mutex::new(Vec::new()));

        for task_id in task_ids {
            if let Some(task) = self.tasks.get(&task_id) {
                let task = Arc::clone(task);
                let task_id = task_id.clone();
                let results = Arc::clone(&results);

                let handle = thread::spawn(move || {
                    let mut task = task.lock().unwrap();
                    task.set_state(TaskState::Running);
                    let result = task.run();
                    results.lock().unwrap().push((task_id, result));
                });

                handles.push(handle);
            }
        }

        // Wait for all tasks to complete
        for handle in handles {
            handle.join().map_err(|_| "Task thread panicked".to_string())?;
        }

        Ok(Arc::try_unwrap(results)
            .unwrap()
            .into_inner()
            .unwrap())
    }

    fn process_task_results(&mut self, results: Vec<(String, Result<(), String>)>) -> Result<(), String> {
        for (task_id, result) in results {
            match result {
                Ok(()) => {
                    if let Some(task) = self.tasks.get(&task_id) {
                        task.lock().unwrap().set_state(TaskState::Complete);
                        self.completed.insert(task_id);
                    }
                }
                Err(e) => {
                    if let Some(task) = self.tasks.get(&task_id) {
                        task.lock().unwrap().set_state(TaskState::Failed(e.clone()));
                    }
                    self.state = WorkflowState::Failed(format!("Task {} failed: {}", task_id, e));
                    return Err(format!("Workflow failed at task {}: {}", task_id, e));
                }
            }
        }
        Ok(())
    }

    fn cleanup_completed_tasks(&mut self) {
        for completed_task in &self.completed {
            self.dependency_graph.remove_task(completed_task);
            self.tasks.remove(completed_task);
        }
    }

    // Keeping the same validation methods from original code
    fn validate(&self) -> Result<(), String> {
        // Check all dependencies exist
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
        let mut dep_map: HashMap<String, Vec<String>> = self.tasks
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

    pub fn state(&self) -> &WorkflowState {
        &self.state
    }
}