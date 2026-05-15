import React, { useEffect } from "react";
import { useFormik } from "formik";
import { useDispatch, useSelector } from "react-redux";
import { Card } from "primereact/card";
import { Button } from "primereact/button";
import { Password } from "primereact/password";
import { InputText } from "primereact/inputtext";
import { Divider } from "primereact/divider";
import { Dialog } from "primereact/dialog";
import { classNames } from "primereact/utils";
import {
  ModifyRegistrationSuccessMessage,
  Register,
} from "../../actions/authActions";
import { useNavigate } from "react-router-dom";
import { Alert } from "@mui/material";

const SignupPage = () => {
  const auth = useSelector((state) => state.auth);

  const dispatch = useDispatch();
  const navigate = useNavigate();

  const formik = useFormik({
    // enableReinitialize set to true to allow form to be re-initialized when the invited user is set
    enableReinitialize: true,
    initialValues: {
      name: "",
      email: "",
      password: "",
    },
    validate: (data) => {
      let errors = {};

      if (!data.name) {
        errors.name = "Name is required.";
      }

      if (!data.email) {
        errors.email = "Email is required.";
      } else if (
        !/^[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,4}$/i.test(data.email)
      ) {
        errors.email = "Invalid email address. E.g. example@email.com";
      }

      if (!data.password) {
        errors.password = "Password is required.";
      }

      if (data.password.length > 0 && data.password.length < 8) {
        errors.password =
          "Password is too short. 8 characters is the minimum length.";
      }

      return errors;
    },
    onSubmit: (values) => {
      dispatch(Register(values.email, values.password, values.name))
        .then((data) => {
          // data will be `res.data` from the thunk
          // success => show success message or navigate
          dispatch(ModifyRegistrationSuccessMessage(true));
        })
        .catch((err) => {
          // If it's fieldErrors => { email: ["already exists"] }
          if (err.fieldErrors) {
            Object.keys(err.fieldErrors).forEach((field) => {
              formik.setFieldError(field, err.fieldErrors[field][0]);
            });
          } else {
            // some other error
            console.error("Register failed:", err);
          }
        });
    },
  });

  // Whenever `auth.fieldErrors` changes, update Formik errors
  useEffect(() => {
    if (auth.fieldErrors) {
      Object.keys(auth.fieldErrors).forEach((field) => {
        // Usually the array has 1 item, so we pick the first message
        formik.setFieldError(field, auth.fieldErrors[field][0]);
      });
    }
  }, [auth.fieldErrors, formik]);

  const isFormFieldValid = (name) =>
    !!(formik.touched[name] && formik.errors[name]);
  const getFormErrorMessage = (name) => {
    return (
      isFormFieldValid(name) && (
        <small className="p-error">{formik.errors[name]}</small>
      )
    );
  };

  const dialogFooterSuccess = (
    <div className="p-d-flex p-jc-center">
      <Button
        label="OK"
        className="p-button-text"
        autoFocus
        onClick={() => {
          dispatch(ModifyRegistrationSuccessMessage(false));
          navigate("/ui");
        }}
      />
    </div>
  );

  const passwordHeader = <h6>Pick a password</h6>;
  const passwordFooter = (
    <React.Fragment>
      <Divider />
      <p className="p-mt-2">Suggestions</p>
      <ul className="p-pl-2 p-ml-2 p-mt-0" style={{ lineHeight: "1.5" }}>
        <li>At least one lowercase</li>
        <li>At least one uppercase</li>
        <li>At least one numeric</li>
        <li>Minimum 8 characters</li>
      </ul>
    </React.Fragment>
  );

  return (
    <div className="sign-up-page">
      <img alt="AI4C logo" src="/ai4c_colored.png" className="login-page-logo" />
      <br />
      <Card className="occ-login-card">
        <h3>Please sign up</h3>

        {/* Show error message if present */}
        {auth.errorMessage && (
          <Alert severity="error" style={{ marginBottom: "1rem" }}>
            {auth.errorMessage}
          </Alert>
        )}

        <Dialog
          visible={auth.showSuccessMessage}
          onHide={() => dispatch(ModifyRegistrationSuccessMessage(false))}
          position="top"
          footer={dialogFooterSuccess}
          showHeader={false}
          breakpoints={{ "960px": "80vw" }}
          style={{ width: "30vw" }}
        >
          <div className="p-d-flex p-ai-center p-dir-col p-pt-6 p-px-3 center-text">
            <br />
            <i
              className="pi pi-check-circle"
              style={{ fontSize: "5rem", color: "var(--green-500)" }}
            />
            <br />
            <h5>Registration Successful!</h5>
            <br />
            <p>
              Your account has been registered under the name <b>{formik.values.name}</b>.
              <br />
              Press 'OK' to proceed to the OCR UI.
            </p>
          </div>
        </Dialog>

        <div className="p-d-flex p-jc-center">
          <div style={{ minWidth: "400px" }}>
            <form onSubmit={formik.handleSubmit} className="p-fluid">
              <div className="p-field">
                <span className="p-float-label p-input-icon-right">
                  <i className="pi pi-envelope" />
                  <InputText
                    id="email"
                    name="email"
                    value={formik.values.email}
                    onChange={formik.handleChange}
                    autoFocus
                    className={classNames({ "p-invalid": isFormFieldValid("email") })}
                  />
                  <label htmlFor="email" className={classNames({ "p-error": isFormFieldValid("email") })}>
                    Email*
                  </label>
                </span>
                {getFormErrorMessage("email")}
              </div>

              <br />

              <div className="p-field">
                <span className="p-float-label">
                  <InputText
                    id="name"
                    name="name"
                    value={formik.values.name}
                    onChange={formik.handleChange}
                    className={classNames({ "p-invalid": isFormFieldValid("name") })}
                  />
                  <label htmlFor="name" className={classNames({ "p-error": isFormFieldValid("name") })}>
                    Name*
                  </label>
                </span>
                {getFormErrorMessage("name")}
              </div>

              <br />

              <div className="p-field">
                <span className="p-float-label">
                  <Password
                    id="password"
                    name="password"
                    value={formik.values.password}
                    onChange={formik.handleChange}
                    toggleMask
                    className={classNames({ "p-invalid": isFormFieldValid("password") })}
                    header={passwordHeader}
                    footer={passwordFooter}
                  />
                  <label htmlFor="password" className={classNames({ "p-error": isFormFieldValid("password") })}>
                    Password*
                  </label>
                </span>
                {getFormErrorMessage("password")}
              </div>

              <br />

              {formik.errors.general && (
                <div style={{ color: "red" }}>{formik.errors.general}</div>
              )}

              <Button type="submit" label="Submit" className="p-mt-2" disabled={auth.loading} />
            </form>
          </div>
        </div>
      </Card>

      <br />
    </div>
  );
};

export default SignupPage;
