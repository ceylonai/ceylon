/*
 * Copyright 2024-Present, Syigen Ltd. and Syigen Private Limited. All rights reserved.
 * Licensed under the Apache License, Version 2.0 (See LICENSE.md or http://www.apache.org/licenses/LICENSE-2.0).
 *
 */
use rajakariya::{ConditionalTask, DataProcessingTask, Workflow, WorkflowError};

// Example usage
fn main() -> Result<(), WorkflowError> {
    // Create a complex workflow
    let mut workflow = Workflow::new(
        "workflow1".to_string(),
        "Complex Data Processing".to_string()
    );

    // Add a data processing task
    let data_task = DataProcessingTask::new(
        "data_task1".to_string(),
        vec![10, 20, 30, 40, 50],
        100
    );
    workflow.add_task(Box::new(data_task));

    // Add a conditional task that depends on the data task
    let condition = Box::new(|| {
        // Some complex condition
        true
    });
    let conditional_task = ConditionalTask::new(
        "conditional_task1".to_string(),
        condition,
        vec!["data_task1".to_string()]
    );
    workflow.add_task(Box::new(conditional_task));

    // Execute the workflow
    match workflow.execute() {
        Ok(_) => println!("Workflow completed successfully"),
        Err(e) => println!("Workflow failed: {}", e),
    }

    Ok(())
}