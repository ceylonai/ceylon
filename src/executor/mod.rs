/// This is the module that has all the executor functions
/// i.e. the functions that have the responsibility of parsing and executing functions.
use std::sync::Arc;

use anyhow::Result;
use log::debug;
use pyo3::prelude::*;
use pyo3_asyncio::TaskLocals;
use crate::types::FunctionInfo;


fn get_function_output<'a, T>(
    function: &'a FunctionInfo,
    py: Python<'a>,
    input: &T,
) -> Result<&'a PyAny, PyErr>
    where
        T: ToPyObject,
{
    let handler = function.handler.as_ref(py);

    // this makes the request object accessible across every route
    match function.number_of_params {
        0 => handler.call0(),
        1 => handler.call1((input.to_object(py), )),
        // this is done to accommodate any future params
        2_u8..=u8::MAX => handler.call1((input.to_object(py), )),
    }
}


pub async fn execute_event_handler(
    event_handler: Option<Arc<FunctionInfo>>,
    task_locals: &TaskLocals,
) -> Result<()> {
    if let Some(function) = event_handler {
        if function.is_async {
            debug!("Startup event handler async");
            Python::with_gil(|py| {
                pyo3_asyncio::into_future_with_locals(
                    task_locals,
                    function.handler.as_ref(py).call0()?,
                )
            })?
                .await?;
        } else {
            debug!("Startup event handler");
            Python::with_gil(|py| function.handler.call0(py))?;
        }
    }
    Ok(())
}