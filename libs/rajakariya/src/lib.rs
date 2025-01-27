mod workflow;

pub mod prelude {
    pub use crate::workflow::{ParallelWorkflow, Task, TaskState, WorkflowState};
}
