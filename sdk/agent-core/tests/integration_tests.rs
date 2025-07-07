use agent_core::lifecycle::{AgentState, LifecycleManager};

#[tokio::test]
async fn lifecycle_test() {
    let mut lifecycle = LifecycleManager::new();
    lifecycle.initialize().await;
    lifecycle.start().await;
    assert_eq!(lifecycle.state, AgentState::Running);
    lifecycle.stop().await;
    assert_eq!(lifecycle.state, AgentState::Stopped);
}
