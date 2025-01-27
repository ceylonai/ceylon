/*
 * Copyright 2024-Present, Syigen Ltd. and Syigen Private Limited. All rights reserved.
 * Licensed under the Apache License, Version 2.0 (See LICENSE.md or http://www.apache.org/licenses/LICENSE-2.0).
 *
 */
use rajakariya::{ConditionalTask, DataProcessingTask, Task, TaskState, Workflow, WorkflowError};

// Example usage
fn main() -> Result<(), WorkflowError> {
    // Create a complex data processing workflow
    let mut workflow = Workflow::new(
        "data_pipeline_001".to_string(),
        "Complex Data Processing Pipeline".to_string(),
    );

    // Task 1: Initial data validation
    let validation_task = DataProcessingTask::new(
        "validate_data".to_string(),
        vec![10, 20, 30, 40, 50],
        25, // Threshold for initial validation
    );

    // Task 2: Data normalization (depends on validation)
    let normalization_task = DataProcessingTask::new(
        "normalize_data".to_string(),
        vec![100, 200, 300, 400, 500],
        250, // Threshold for normalized data
    );

    // Task 3: Feature extraction (depends on normalization)
    let feature_extraction_task = DataProcessingTask::new(
        "extract_features".to_string(),
        vec![15, 25, 35, 45, 55],
        30, // Threshold for feature extraction
    );

    // Task 4A: Primary analysis (depends on feature extraction)
    let primary_analysis_task = DataProcessingTask::new(
        "primary_analysis".to_string(),
        vec![60, 70, 80, 90, 100],
        75, // Threshold for primary analysis
    );

    // Task 4B: Secondary analysis (depends on feature extraction)
    let secondary_analysis_task = DataProcessingTask::new(
        "secondary_analysis".to_string(),
        vec![30, 40, 50, 60, 70],
        45, // Threshold for secondary analysis
    );

    // Task 5: Final aggregation (depends on both analyses)
    let final_aggregation_task = DataProcessingTask::new(
        "final_aggregation".to_string(),
        vec![150, 160, 170, 180, 190],
        165, // Threshold for final aggregation
    );

    // Conditional task: Quality check (depends on both analyses)
    let quality_check_task = ConditionalTask::new(
        "quality_check".to_string(),
        Box::new(|| {
            // Simulate some condition based on external factors
            let quality_threshold = 0.95;
            let current_quality = 0.97;
            current_quality >= quality_threshold
        }),
        vec![
            "primary_analysis".to_string(),
            "secondary_analysis".to_string(),
        ],
    );

    // Create dependency chain using a custom implementation
    struct DependentTask {
        task: Box<dyn Task>,
        dependencies: Vec<String>,
    }

    impl DependentTask {
        fn new(task: Box<dyn Task>, dependencies: Vec<String>) -> Self {
            Self { task, dependencies }
        }
    }

    // Define tasks with their dependencies
    let tasks = vec![
        DependentTask::new(Box::new(validation_task), vec![]),
        DependentTask::new(
            Box::new(normalization_task),
            vec!["validate_data".to_string()],
        ),
        DependentTask::new(
            Box::new(feature_extraction_task),
            vec!["normalize_data".to_string()],
        ),
        DependentTask::new(
            Box::new(primary_analysis_task),
            vec!["extract_features".to_string()],
        ),
        DependentTask::new(
            Box::new(secondary_analysis_task),
            vec!["extract_features".to_string()],
        ),
        DependentTask::new(
            Box::new(quality_check_task),
            vec![
                "primary_analysis".to_string(),
                "secondary_analysis".to_string(),
            ],
        ),
        DependentTask::new(
            Box::new(final_aggregation_task),
            vec![
                "primary_analysis".to_string(),
                "secondary_analysis".to_string(),
                "quality_check".to_string(),
            ],
        ),
    ];

    // Add tasks to workflow
    for dependent_task in tasks {
        let mut task = dependent_task.task;

        // Create a wrapper that implements Task and includes dependencies
        struct TaskWrapper {
            inner: Box<dyn Task>,
            deps: Vec<String>,
        }

        impl Task for TaskWrapper {
            fn execute(&mut self) -> Result<(), WorkflowError> {
                self.inner.execute()
            }

            fn validate(&self) -> Result<(), WorkflowError> {
                self.inner.validate()
            }

            fn get_state(&self) -> &TaskState {
                self.inner.get_state()
            }

            fn set_state(&mut self, state: TaskState) {
                self.inner.set_state(state)
            }

            fn get_id(&self) -> &str {
                self.inner.get_id()
            }

            fn get_dependencies(&self) -> Vec<String> {
                self.deps.clone()
            }

            fn should_execute(&self) -> bool {
                self.inner.should_execute()
            }
        }

        workflow.add_task(Box::new(TaskWrapper {
            inner: task,
            deps: dependent_task.dependencies,
        }));
    }

    // Execute the workflow
    println!("Starting workflow execution...");
    match workflow.execute() {
        Ok(_) => {
            println!("Workflow completed successfully!");
            Ok(())
        }
        Err(e) => {
            println!("Workflow failed: {}", e);
            Err(e)
        }
    }
}
