use async_trait::async_trait;
use rajakariya::prelude::{AsyncGraph, AsyncTask};
use std::error::Error;
use std::time::Duration;

// Simulated task that processes data
#[derive(Debug)]
struct DataProcessingTask {
    id: String,
    dependencies: Vec<String>,
    processing_time: Duration,
}

#[async_trait]
impl AsyncTask for DataProcessingTask {
    fn id(&self) -> &str {
        &self.id
    }

    fn dependencies(&self) -> &[String] {
        &self.dependencies
    }

    async fn execute(&self) -> Result<(), String> {
        println!("Starting task: {}", self.id);
        tokio::time::sleep(self.processing_time).await;
        println!("Completed task: {}", self.id);
        Ok(())
    }
}

// Simulated task that makes an HTTP request
#[derive(Debug)]
struct APITask {
    id: String,
    dependencies: Vec<String>,
    endpoint: String,
}

#[async_trait]
impl AsyncTask for APITask {
    fn id(&self) -> &str {
        &self.id
    }

    fn dependencies(&self) -> &[String] {
        &self.dependencies
    }

    async fn execute(&self) -> Result<(), String> {
        println!("Making API call to {} for task {}", self.endpoint, self.id);
        // Simulate API call with random delay
        tokio::time::sleep(Duration::from_millis(500)).await;
        println!("API call completed for task {}", self.id);
        Ok(())
    }
}

#[tokio::main]
async fn main() -> Result<(), Box<dyn Error>> {
    // Create a new graph
    let mut graph = AsyncGraph::new();

    // Add initial data loading tasks (no dependencies)
    graph.add_task(Box::new(DataProcessingTask {
        id: "load_user_data".to_string(),
        dependencies: vec![],
        processing_time: Duration::from_millis(1000),
    }))?;

    graph.add_task(Box::new(DataProcessingTask {
        id: "load_product_data".to_string(),
        dependencies: vec![],
        processing_time: Duration::from_millis(800),
    }))?;

    // Add API tasks that depend on data loading
    graph.add_task(Box::new(APITask {
        id: "fetch_user_preferences".to_string(),
        dependencies: vec!["load_user_data".to_string()],
        endpoint: "api/preferences".to_string(),
    }))?;

    graph.add_task(Box::new(APITask {
        id: "fetch_product_inventory".to_string(),
        dependencies: vec!["load_product_data".to_string()],
        endpoint: "api/inventory".to_string(),
    }))?;

    // Add final processing task that depends on all previous tasks
    graph.add_task(Box::new(DataProcessingTask {
        id: "generate_recommendations".to_string(),
        dependencies: vec![
            "fetch_user_preferences".to_string(),
            "fetch_product_inventory".to_string(),
        ],
        processing_time: Duration::from_millis(1500),
    }))?;

    // Execute the graph
    println!("Starting task execution...");
    match graph.execute().await {
        Ok(()) => {
            println!("All tasks completed successfully!");
            println!("Graph status: {:?}", graph.status());
        }
        Err(e) => {
            println!("Error executing tasks: {}", e);
            println!("Graph status: {:?}", graph.status());
        }
    }

    Ok(())
}
