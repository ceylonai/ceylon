use pyo3::{pyclass, pymethods, Py, PyObject, PyResult};
use pyo3::types::PyFunction;
use crossbeam::channel::{unbounded, Sender, Receiver};
use std::thread;

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
        thread::spawn(move || {
            sender.send(message).unwrap();  // Send the message
        });
        Ok(())
    }

    pub fn start(&mut self) -> PyResult<()> {
        println!("{:?} start ", self.name);
        if let Some(receiver) = self.receiver.take() {
            let name = self.name.clone();
            thread::spawn(move || {
                loop {
                    match receiver.recv() {
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
            });
        }
        Ok(())
    }
}
