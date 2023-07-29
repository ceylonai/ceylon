use anyhow::Result;
use log::debug;
use pyo3::prelude::*;
use pyo3_asyncio::TaskLocals;

use crate::types::FunctionInfo;

#[inline]
pub async fn execute_process_function(
    input: PyObject,
    function: &FunctionInfo,
    task_locals: &TaskLocals,
) -> Result<()> {
    if function.is_async {
        debug!("Process event handler async");
        Python::with_gil(|py| {
            pyo3_asyncio::into_future_with_locals(
                task_locals,
                function.handler.as_ref(py).call1((input.to_object(py),))?,
            )
        })?
        .await?;
    } else {
        debug!("Process event handler");
        Python::with_gil(|py| function.handler.call0(py))?;
    }
    Ok(())
}

#[inline]
pub async fn execute_process_function_only(
    function: &FunctionInfo,
    task_locals: &TaskLocals,
) -> Result<()> {
    if function.is_async {
        debug!("Process event handler async");
        Python::with_gil(|py| {
            pyo3_asyncio::into_future_with_locals(task_locals, function.handler.as_ref(py).call0()?)
        })?
        .await?;
    } else {
        debug!("Process event handler");
        Python::with_gil(|py| function.handler.call0(py))?;
    }
    Ok(())
}
