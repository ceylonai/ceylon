use std::sync::Arc;
use std::thread;
use std::time::Duration;
use rajakariya::{ParallelWorkflow, Task, TaskState, WorkflowState};

// Define a basic task structure
#[derive(Debug)]
struct ProcessingTask {
    id: String,
    state: TaskState,
    dependencies: Vec<String>,
    processing_time: Duration,
}

impl ProcessingTask {
    fn new(id: &str, processing_time: Duration, dependencies: Vec<String>) -> Self {
        ProcessingTask {
            id: id.to_string(),
            state: TaskState::Ready,
            dependencies,
            processing_time,
        }
    }
}

// Implement the Task trait for ProcessingTask
impl Task for ProcessingTask {
    fn id(&self) -> &str {
        &self.id
    }

    fn run(&mut self) -> Result<(), String> {
        println!("Starting task: {}", self.id);
        thread::sleep(self.processing_time);
        println!("Completed task: {}", self.id);
        Ok(())
    }

    fn state(&self) -> &TaskState {
        &self.state
    }

    fn set_state(&mut self, state: TaskState) {
        self.state = state;
    }

    fn dependencies(&self) -> &[String] {
        &self.dependencies
    }
}

fn main() -> Result<(), String> {
    // Create a new workflow
    let mut workflow = ParallelWorkflow::new("data_processing".to_string());

    // Create tasks with dependencies
    let task1 = ProcessingTask::new(
        "load_data",
        Duration::from_secs(2),
        vec![],
    );

    let task2 = ProcessingTask::new(
        "validate_data",
        Duration::from_secs(1),
        vec!["load_data".to_string()],
    );

    let task3 = ProcessingTask::new(
        "process_data",
        Duration::from_secs(3),
        vec!["validate_data".to_string()],
    );

    let task4 = ProcessingTask::new(
        "generate_report",
        Duration::from_secs(2),
        vec!["process_data".to_string()],
    );

    // Add tasks to workflow
    workflow.add_task(Box::new(task1))?;
    workflow.add_task(Box::new(task2))?;
    workflow.add_task(Box::new(task3))?;
    workflow.add_task(Box::new(task4))?;

    // Validate the workflow
    workflow.validate()?;

    // Execute tasks in parallel based on dependencies
    workflow.set_state(WorkflowState::Running);

    while !workflow.is_empty() {
        // Get tasks that are ready to run (no dependencies)
        let ready_tasks = workflow.get_tasks_with_no_dependencies();

        // Create threads for each ready task
        let mut handles = vec![];

        for task_id in ready_tasks {
            if let Some(task) = workflow.get_task(&task_id) {
                let task_clone = Arc::clone(task);

                let handle = thread::spawn(move || {
                    let mut task = task_clone.lock().unwrap();
                    task.set_state(TaskState::Running);

                    match task.run() {
                        Ok(()) => {
                            task.set_state(TaskState::Complete);
                            true
                        }
                        Err(e) => {
                            task.set_state(TaskState::Failed(e));
                            false
                        }
                    }
                });

                handles.push((task_id, handle));
            }
        }

        // Wait for all spawned tasks to complete
        for (task_id, handle) in handles {
            match handle.join() {
                Ok(success) => {
                    if success {
                        workflow.mark_completed(task_id);
                    } else {
                        workflow.set_state(WorkflowState::Failed(format!("Task {} failed", task_id)));
                        return Err(format!("Workflow failed at task {}", task_id));
                    }
                }
                Err(_) => {
                    workflow.set_state(WorkflowState::Failed("Thread panic occurred".to_string()));
                    return Err("Thread panic occurred".to_string());
                }
            }
        }

        // Clean up completed tasks and update the dependency graph
        workflow.cleanup_completed_tasks();
    }

    workflow.set_state(WorkflowState::Complete);
    println!("Workflow completed successfully!");
    Ok(())
}