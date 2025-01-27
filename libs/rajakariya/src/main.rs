use std::fs;
use std::path::Path;
use std::sync::atomic::{AtomicBool, Ordering};
use std::sync::Arc;
use rajakariya::{TaskState, ParallelWorkflow};
use rajakariya::Task; // Assuming this is from our previous implementation

// Data validation task with thread-safe status tracking
struct DataValidationTask {
    id: String,
    state: TaskState,
    input_path: String,
    required_fields: Vec<String>,
    deps: Vec<String>,
    is_running: Arc<AtomicBool>,
}

impl DataValidationTask {
    fn new(id: String, input_path: String, required_fields: Vec<String>) -> Self {
        Self {
            id,
            state: TaskState::Ready,
            input_path,
            required_fields,
            deps: Vec::new(),
            is_running: Arc::new(AtomicBool::new(false)),
        }
    }
}

impl Task for DataValidationTask {
    fn id(&self) -> &str { &self.id }

    fn run(&mut self) -> Result<(), String> {
        self.is_running.store(true, Ordering::SeqCst);
        println!("🔍 [{}] Validating data in: {}", self.id, self.input_path);

        if !Path::new(&self.input_path).exists() {
            self.is_running.store(false, Ordering::SeqCst);
            return Err(format!("Input file {} not found", self.input_path));
        }

        // Simulate field validation with some delay to show parallel execution
        std::thread::sleep(std::time::Duration::from_secs(1));
        println!("✓ [{}] Verified required fields: {:?}", self.id, self.required_fields);

        self.is_running.store(false, Ordering::SeqCst);
        Ok(())
    }

    fn state(&self) -> &TaskState { &self.state }
    fn set_state(&mut self, state: TaskState) { self.state = state; }
    fn dependencies(&self) -> &[String] { &self.deps }
}

// Data transformation task with thread-safe status tracking
struct DataTransformTask {
    id: String,
    state: TaskState,
    input_path: String,
    output_path: String,
    deps: Vec<String>,
    is_running: Arc<AtomicBool>,
}

impl DataTransformTask {
    fn new(id: String, input_path: String, output_path: String, deps: Vec<String>) -> Self {
        Self {
            id,
            state: TaskState::Ready,
            input_path,
            output_path,
            deps,
            is_running: Arc::new(AtomicBool::new(false)),
        }
    }
}

impl Task for DataTransformTask {
    fn id(&self) -> &str { &self.id }

    fn run(&mut self) -> Result<(), String> {
        self.is_running.store(true, Ordering::SeqCst);
        println!("🔄 [{}] Transforming data from {} to {}",
                 self.id, self.input_path, self.output_path);

        // Simulate transformation work with delay to show parallel execution
        std::thread::sleep(std::time::Duration::from_secs(2));

        fs::write(&self.output_path, format!("transformed data for {}", self.id))
            .map_err(|e| format!("Failed to write output: {}", e))?;

        println!("✓ [{}] Data transformed successfully", self.id);
        self.is_running.store(false, Ordering::SeqCst);
        Ok(())
    }

    fn state(&self) -> &TaskState { &self.state }
    fn set_state(&mut self, state: TaskState) { self.state = state; }
    fn dependencies(&self) -> &[String] { &self.deps }
}

// Report generation task with thread-safe status tracking
struct ReportTask {
    id: String,
    state: TaskState,
    input_paths: Vec<String>,
    output_path: String,
    deps: Vec<String>,
    is_running: Arc<AtomicBool>,
}

impl ReportTask {
    fn new(id: String, input_paths: Vec<String>, output_path: String, deps: Vec<String>) -> Self {
        Self {
            id,
            state: TaskState::Ready,
            input_paths,
            output_path,
            deps,
            is_running: Arc::new(AtomicBool::new(false)),
        }
    }
}

impl Task for ReportTask {
    fn id(&self) -> &str { &self.id }

    fn run(&mut self) -> Result<(), String> {
        self.is_running.store(true, Ordering::SeqCst);
        println!("📊 [{}] Generating report from {:?}", self.id, self.input_paths);

        // Verify all input files exist
        for path in &self.input_paths {
            if !Path::new(path).exists() {
                self.is_running.store(false, Ordering::SeqCst);
                return Err(format!("Input file {} not found", path));
            }
        }

        // Simulate report generation with delay
        std::thread::sleep(std::time::Duration::from_secs(3));

        fs::write(&self.output_path, "report content")
            .map_err(|e| format!("Failed to write report: {}", e))?;

        println!("✓ [{}] Report generated at {}", self.id, self.output_path);
        self.is_running.store(false, Ordering::SeqCst);
        Ok(())
    }

    fn state(&self) -> &TaskState { &self.state }
    fn set_state(&mut self, state: TaskState) { self.state = state; }
    fn dependencies(&self) -> &[String] { &self.deps }
}

fn main() -> Result<(), String> {
    // Create temporary paths for our example
    let input_path = "data.csv";
    let transformed_path_1 = "transformed_1.csv";
    let transformed_path_2 = "transformed_2.csv";
    let report_path = "final_report.pdf";

    // Create a test input file
    fs::write(input_path, "test data")
        .map_err(|e| format!("Failed to create test file: {}", e))?;

    // Initialize parallel workflow
    let mut workflow = ParallelWorkflow::new("data_processing".to_string());

    // Add validation task
    let validation_task = DataValidationTask::new(
        "validate_input".to_string(),
        input_path.to_string(),
        vec!["date".to_string(), "value".to_string(), "category".to_string()]
    );
    workflow.add_task(Box::new(validation_task))?;

    // Add two parallel transformation tasks
    let transform_task_1 = DataTransformTask::new(
        "transform_1".to_string(),
        input_path.to_string(),
        transformed_path_1.to_string(),
        vec!["validate_input".to_string()]
    );
    workflow.add_task(Box::new(transform_task_1))?;

    let transform_task_2 = DataTransformTask::new(
        "transform_2".to_string(),
        input_path.to_string(),
        transformed_path_2.to_string(),
        vec!["validate_input".to_string()]
    );
    workflow.add_task(Box::new(transform_task_2))?;

    // Add final report task that depends on both transformations
    let report_task = ReportTask::new(
        "generate_report".to_string(),
        vec![transformed_path_1.to_string(), transformed_path_2.to_string()],
        report_path.to_string(),
        vec!["transform_1".to_string(), "transform_2".to_string()]
    );
    workflow.add_task(Box::new(report_task))?;

    // Run the parallel workflow
    println!("Starting parallel workflow execution...\n");
    match workflow.run() {
        Ok(()) => {
            println!("\n✅ Workflow completed successfully!");
            println!("Final report generated at: {}", report_path);
        }
        Err(e) => {
            println!("\n❌ Workflow failed: {}", e);
            // Cleanup temporary files
            cleanup_files(&[input_path, transformed_path_1, transformed_path_2, report_path]);
            return Err(e);
        }
    }

    // Cleanup temporary files
    cleanup_files(&[input_path, transformed_path_1, transformed_path_2, report_path]);
    Ok(())
}

fn cleanup_files(paths: &[&str]) {
    for path in paths {
        let _ = fs::remove_file(path);
    }
}