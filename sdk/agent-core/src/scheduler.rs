use std::time::Duration;
use tokio::time::Interval;

pub struct Scheduler;

impl Scheduler {
    pub fn schedule<F>(task: F, interval: Duration) -> Interval
    where
        F: FnMut() + Send + 'static{
        todo!()
    }
}
