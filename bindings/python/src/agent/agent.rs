use pyo3::{pyclass, pymethods, Py, PyObject, PyResult, Python};
use pyo3::types::PyFunction;
use async_std::channel::{unbounded, Sender, Receiver};
use async_std::task;
use pyo3::exceptions::asyncio;

#[pyclass]
pub struct AbstractAgent {
    pub name: String,
    pub fnc: Py<PyFunction>,
    pub sender: Sender<PyObject>,
    pub receiver: Option<Receiver<PyObject>>,
}

#[pymethods]
impl AbstractAgent {
    #[new]
    pub fn new(name: &str, fnc: &PyFunction) -> Self {
        let (tx, rx) = unbounded();

        Self {
            name: name.to_string(),
            fnc: fnc.into(),
            sender: tx,
            receiver: Some(rx),  // Initialize receiver
        }
    }

    pub fn send(&self, message: PyObject) -> PyResult<()> {
        println!("{:?} send message {:?} ", self.name, message);
        let sender = self.sender.clone();
        task::spawn(async move {
            sender.send(message).await.unwrap();  // Send the message
        });
        Ok(())
    }

    pub fn start(&mut self) -> PyResult<()> {
        println!("{:?} start ", self.name);
        if let Some(receiver) = self.receiver.take() {
            let name = self.name.clone();
            let fnc = self.fnc.clone();
            task::spawn(async move {
                loop {
                    let name_clone = name.clone();
                    match receiver.recv().await {
                        Ok(message) => {
                            println!("{:?} received 1 message {:?}", name_clone.clone(), message);
                            Python::with_gil(|py| {
                                let _ = fnc.call1(py, (name_clone, message, ));
                            });
                        }
                        Err(err) => {
                            println!("Error receiving message: {:?}", err);
                            break;
                        }
                    }
                }
            });
        }
        Ok(())
    }
}

impl AbstractAgent {
    async fn receive_messages(&self, receiver: Receiver<PyObject>, name: String) {
        loop {
            match receiver.recv().await {
                Ok(message) => {
                    println!("{:?} received message {:?}", name, message);
                    // Here you can process the message
                }
                Err(err) => {
                    println!("Error receiving message: {:?}", err);
                    break;
                }
            }
        }
    }
}
