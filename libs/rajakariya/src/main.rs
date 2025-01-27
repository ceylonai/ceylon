/*
 * Copyright 2024-Present, Syigen Ltd. and Syigen Private Limited. All rights reserved.
 * Licensed under the Apache License, Version 2.0 (See LICENSE.md or http://www.apache.org/licenses/LICENSE-2.0).
 *
 */
use rajakariya::{SimpleTask, WorkflowEngine, WorkflowError};

// Example usage
fn main() -> Result<(), WorkflowError> {
    let mut engine = WorkflowEngine::new();

    // Create a workflow
    let workflow_id = engine.create_workflow("Simple Workflow".to_string());

    // Add tasks
    if let Some(workflow) = engine.get_workflow_mut(&workflow_id) {
        workflow.add_task(Box::new(SimpleTask::new("Task 1".to_string())));
        workflow.add_task(Box::new(SimpleTask::new("Task 2".to_string())));
    }

    // Execute workflow
    engine.execute_workflow(&workflow_id)?;

    // Check final state
    if let Some(workflow) = engine.get_workflow(&workflow_id) {
        println!("Workflow final state: {:?}", workflow.get_state());
    }

    Ok(())
}
