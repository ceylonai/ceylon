use pyo3::{Py, pyclass, pymethods, PyObject, PyResult};
use pyo3::types::PyFunction;

#[pyclass]
pub struct AbstractAgent {
    pub name: String,
    pub fnc: Py<PyFunction>,
}

#[pymethods]
impl AbstractAgent {
    #[new]
    pub fn new(name: &str, fnc: &PyFunction) -> Self {
        Self {
            name: name.to_string(),
            fnc: fnc.into(),
        }
    }

    pub async fn send(&mut self, message: PyObject) -> PyResult<()> {
        println!("{:?} send message {:?} ", self.name, message);
        // self.node.connect(8888, "test_topic");
        // async_std::task::block_on(async move {
        //     self.node.run().await;
        // });
        Ok(())
    }

    pub async fn start(&mut self) {
        println!("{:?} start ", self.name);
        // self.node.connect(8888, "test_topic");
        // async_std::task::block_on(async move {
        //     self.node.run().await;
        // });
    }
    //
    // pub async fn send_message(&mut self, message: &str) {
    //     // self.node.broadcast(message.as_bytes()).unwrap();
    // }
}