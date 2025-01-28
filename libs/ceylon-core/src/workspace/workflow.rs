/*
 * Copyright 2024-Present, Syigen Ltd. and Syigen Private Limited. All rights reserved.
 * Licensed under the Apache License, Version 2.0 (See LICENSE.md or http://www.apache.org/licenses/LICENSE-2.0).
 *
 */

use crate::{AgentDetail, EventHandler, MessageHandler, Processor};
use async_trait::async_trait;
use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use std::fmt::Debug;
use std::sync::Arc;
use tokio::sync::RwLock;

// Task status enum
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub enum TaskStatus {
    Pending,
    InProgress,
    Completed,
    Failed,
}

// Task definition
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Task {
    pub id: String,
    pub data: Vec<u8>,
    pub status: TaskStatus,
    pub assigned_to: Option<String>,
    pub result: Option<Vec<u8>>,
}

// Task message types
#[derive(Debug, Clone, Serialize, Deserialize)]
pub enum TaskMessage {
    Submit(Task),
    StatusUpdate { task_id: String, status: TaskStatus },
    Complete { task_id: String, result: Vec<u8> },
}

// Task Manager implementation
#[derive(Debug)]
pub struct TaskManager {
    tasks: Arc<RwLock<HashMap<String, Task>>>,
    agent_details: Arc<RwLock<HashMap<String, AgentDetail>>>,
}

impl Default for TaskManager {
    fn default() -> Self {
        Self::new()
    }
}

impl TaskManager {
    pub fn new() -> Self {
        TaskManager {
            tasks: Arc::new(RwLock::new(HashMap::new())),
            agent_details: Arc::new(RwLock::new(HashMap::new())),
        }
    }

    pub async fn submit_task(&self, task: Task) -> String {
        let mut tasks = self.tasks.write().await;
        let task_id = task.id.clone();
        tasks.insert(task_id.clone(), task);
        task_id
    }

    pub async fn assign_task(&self, task_id: String, agent_id: String) -> bool {
        let mut tasks = self.tasks.write().await;
        if let Some(task) = tasks.get_mut(task_id.as_str()) {
            if task.status == TaskStatus::Pending {
                task.status = TaskStatus::InProgress;
                task.assigned_to = Some(agent_id.to_string());
                return true;
            }
        }
        false
    }

    pub async fn complete_task(&self, task_id: String, result: Vec<u8>) -> bool {
        let mut tasks = self.tasks.write().await;
        if let Some(task) = tasks.get_mut(task_id.as_str()) {
            task.status = TaskStatus::Completed;
            task.result = Some(result);
            return true;
        }
        false
    }

    pub async fn get_pending_tasks(&self) -> Vec<Task> {
        let tasks = self.tasks.read().await;
        tasks
            .values()
            .filter(|task| task.status == TaskStatus::Pending)
            .cloned()
            .collect()
    }
}

// Message Handler implementation
#[derive(Debug)]
pub struct TaskMessageHandler {
    task_manager: Arc<TaskManager>,
    agent: AgentDetail,
}

#[async_trait]
impl MessageHandler for TaskMessageHandler {
    async fn on_message(&self, agent: AgentDetail, data: Vec<u8>, _time: u64) {
        let message: TaskMessage = serde_json::from_slice(&data).unwrap();
        match message {
            TaskMessage::Submit(task) => {
                self.task_manager.submit_task(task).await;
            }
            TaskMessage::StatusUpdate { task_id, status } => {
                if let Some(task) = self.task_manager.tasks.write().await.get_mut(&task_id) {
                    task.status = status;
                }
            }
            TaskMessage::Complete { task_id, result } => {
                self.task_manager.complete_task(task_id, result).await;
            }
        }
    }
}

// Task Processor implementation
#[derive(Debug)]
pub struct TaskProcessor {
    task_manager: Arc<TaskManager>,
}

#[async_trait]
impl Processor for TaskProcessor {
    async fn run(&self, input: Vec<u8>) -> () {
        let pending_tasks = self.task_manager.get_pending_tasks().await;
        for task in pending_tasks {
            // Process task logic here
            let result = vec![]; // Replace with actual processing
            self.task_manager.complete_task(task.id, result).await;
        }
    }
}

// Event Handler implementation
#[derive(Debug)]
pub struct TaskEventHandler {
    task_manager: Arc<TaskManager>,
}

#[async_trait]
impl EventHandler for TaskEventHandler {
    async fn on_agent_connected(&self, _topic: String, agent: AgentDetail) -> () {
        self.task_manager
            .agent_details
            .write()
            .await
            .insert(agent.id.clone(), agent);
    }
}

// Helper function to create a new task
pub fn create_task(id: String, data: Vec<u8>) -> Task {
    Task {
        id,
        data,
        status: TaskStatus::Pending,
        assigned_to: None,
        result: None,
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use tokio::runtime::Runtime;

    #[test]
    fn test_workflow_components() {
        // Create async runtime for testing
        let rt = Runtime::new().unwrap();
        rt.block_on(async {
            // Initialize TaskManager
            let task_manager = Arc::new(TaskManager::new());

            // Test task creation and submission
            let test_task = create_task("task1".to_string(), "test data".as_bytes().to_vec());
            let task_id = task_manager.submit_task(test_task.clone()).await;
            assert_eq!(task_id, "task1");

            // Test task assignment
            let agent_id = "agent1";
            let assigned = task_manager.assign_task(&task_id, agent_id).await;
            assert!(assigned);

            let tasks = task_manager.tasks.read().await;
            let assigned_task = tasks.get(&task_id).unwrap();
            assert_eq!(assigned_task.status, TaskStatus::InProgress);
            assert_eq!(assigned_task.assigned_to, Some(agent_id.to_string()));

            // Test task completion
            let result = "completed result".as_bytes().to_vec();
            let completed = task_manager.complete_task(task_id.clone(), result.clone()).await;
            assert!(completed);

            let tasks = task_manager.tasks.read().await;
            let completed_task = tasks.get(&task_id).unwrap();
            assert_eq!(completed_task.status, TaskStatus::Completed);
            assert_eq!(completed_task.result, Some(result));

            // Test TaskMessageHandler
            let agent = AgentDetail {
                name: "Test Agent".to_string(),
                id: "agent1".to_string(),
                role: "worker".to_string(),
            };

            let message_handler = TaskMessageHandler {
                task_manager: task_manager.clone(),
                agent: agent.clone(),
            };

            // Test submit message handling
            let new_task = create_task("task2".to_string(), "new test data".as_bytes().to_vec());
            let submit_message = TaskMessage::Submit(new_task);
            let message_data = serde_json::to_vec(&submit_message).unwrap();

            message_handler
                .on_message(agent.clone(), message_data, 0)
                .await;

            let tasks = task_manager.tasks.read().await;
            assert!(tasks.contains_key("task2"));

            // Test TaskEventHandler
            let event_handler = TaskEventHandler {
                task_manager: task_manager.clone(),
            };

            let new_agent = AgentDetail {
                name: "New Agent".to_string(),
                id: "agent2".to_string(),
                role: "worker".to_string(),
            };

            event_handler
                .on_agent_connected("test_topic".to_string(), new_agent.clone())
                .await;

            let connected_agents = task_manager.agent_details.read().await;
            assert!(connected_agents.contains_key(&new_agent.id));
            assert_eq!(
                connected_agents.get(&new_agent.id).unwrap().name,
                new_agent.name
            );

            // Test TaskProcessor
            let processor = TaskProcessor {
                task_manager: task_manager.clone(),
            };

            // Submit a pending task
            let pending_task = create_task("task3".to_string(), "pending data".as_bytes().to_vec());
            task_manager.submit_task(pending_task).await;

            // Run processor
            processor.run(vec![]).await;

            // Verify task was processed
            let tasks = task_manager.tasks.read().await;
            let processed_task = tasks.get("task3").unwrap();
            assert_eq!(processed_task.status, TaskStatus::Completed);
        });
    }

    #[test]
    fn test_task_status_transitions() {
        let rt = Runtime::new().unwrap();
        rt.block_on(async {
            let task_manager = Arc::new(TaskManager::new());

            // Create and submit task
            let test_task = create_task("status_test".to_string(), "test data".as_bytes().to_vec());
            let task_id = task_manager.submit_task(test_task).await;

            // Verify initial status
            let tasks = task_manager.tasks.read().await;
            let task = tasks.get(&task_id).unwrap();
            assert_eq!(task.status, TaskStatus::Pending);

            // Test invalid task assignment
            let invalid_assigned = task_manager.assign_task("invalid_id", "agent1").await;
            assert!(!invalid_assigned);

            // Test valid task assignment
            let assigned = task_manager.assign_task(&task_id, "agent1").await;
            assert!(assigned);

            let tasks = task_manager.tasks.read().await;
            let task = tasks.get(&task_id).unwrap();
            assert_eq!(task.status, TaskStatus::InProgress);

            // Test completion
            let completed = task_manager.complete_task(task_id.clone(), vec![1, 2, 3]).await;
            assert!(completed);

            let tasks = task_manager.tasks.read().await;
            let task = tasks.get(&task_id).unwrap();
            assert_eq!(task.status, TaskStatus::Completed);
        });
    }

    #[test]
    fn test_pending_tasks_retrieval() {
        let rt = Runtime::new().unwrap();
        rt.block_on(async {
            let task_manager = Arc::new(TaskManager::new());

            // Create multiple tasks with different statuses
            let pending_task1 = create_task("pending1".to_string(), "data1".as_bytes().to_vec());
            let pending_task2 = create_task("pending2".to_string(), "data2".as_bytes().to_vec());
            let in_progress_task =
                create_task("in_progress".to_string(), "data3".as_bytes().to_vec());
            let completed_task = create_task("completed".to_string(), "data4".as_bytes().to_vec());

            // Submit all tasks
            task_manager.submit_task(pending_task1).await;
            task_manager.submit_task(pending_task2).await;
            task_manager.submit_task(in_progress_task).await;
            task_manager.submit_task(completed_task).await;

            // Change status of some tasks
            task_manager.assign_task("in_progress", "agent1").await;
            task_manager.complete_task("completed".to_string(), vec![]).await;

            // Get pending tasks
            let pending_tasks = task_manager.get_pending_tasks().await;

            // Verify only pending tasks are returned
            assert_eq!(pending_tasks.len(), 2);
            assert!(pending_tasks
                .iter()
                .all(|task| task.status == TaskStatus::Pending));
            assert!(pending_tasks.iter().any(|task| task.id == "pending1"));
            assert!(pending_tasks.iter().any(|task| task.id == "pending2"));
        });
    }
}
