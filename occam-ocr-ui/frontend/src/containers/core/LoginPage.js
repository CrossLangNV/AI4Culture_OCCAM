import React, { useEffect, useRef } from "react";
import { useDispatch, useSelector } from "react-redux";
import { Login } from "../../actions/authActions";
import { useLocation, useNavigate } from "react-router-dom";
import { Toast } from "primereact/toast";
import { Card } from "primereact/card";
import { useFormik } from "formik";
import * as Yup from "yup";
import { Password } from "primereact/password";
import { InputText } from "primereact/inputtext";
import { Button } from "primereact/button";

const LoginPage = () => {
  const dispatch = useDispatch();
  const navigate = useNavigate();
  const location = useLocation();
  const toast = useRef(null);

  const auth = useSelector((state) => state.auth);

  const onLoginSuccess = () => {
    // location.state?.from is the route user originally wanted
    const from = location.state?.from?.pathname || "/ui";
    navigate(from);
  };

  const formik = useFormik({
    initialValues: {
      email: "",
      password: "",
    },
    onSubmit: (values) => {
      dispatch(Login(values.email, values.password, onLoginSuccess));
    },
    validationSchema: Yup.object({
      email: Yup.string()
        .trim()
        .email("Invalid email address")
        .required("Email is required"),
      password: Yup.string().trim().required("Password is required"),
    }),
  });

  return (
    <div className="occ-login">
      {/*<Row>*/}
      {/*    <Col className={"center-div"}>*/}
      <img
        alt="AI4C logo"
        src="/ai4c_colored.png"
        className="d-inline-block login-page-logo"
      />
      <br />
      {/*<span className="occ-branding-login"> {uiStates.themeConfig.name}</span>*/}
      {/*</Col>*/}

      {/*</Row>*/}

      <Card className="occ-login-card grid">
        <h3>Please sign in</h3>

        <form onSubmit={formik.handleSubmit}>
          <InputText
            id="email"
            type="email"
            placeholder="Email"
            name="email"
            value={formik.values.email}
            onChange={formik.handleChange}
            className="col-12"
          />
          {formik.errors.email ? (
            <div className="text-sm" style={{ color: "#d95b5b" }}>
              {formik.errors.email}{" "}
            </div>
          ) : null}
          <br />
          <Password
            id="password"
            name="password"
            placeholder="Password"
            feedback={false}
            toggleMask
            value={formik.values.password}
            onChange={formik.handleChange}
            className="col-12 p-0 mt-2"
          />
          {formik.errors.password ? (
            <div className="text-sm" style={{ color: "#d95b5b" }}>
              {formik.errors.password}{" "}
            </div>
          ) : null}
          <br />
          <br />
          <button
            type="button"
            className="btn-link mt-2"
            onClick={() => navigate("/signup")}
          >
            Don't have an account? Sign up.
          </button>
          <br />
          <br />
          <Button
            type="submit"
            label="Sign in"
            className="pl-4 pr-4 mt-2"
            disabled={auth.loading}
          />
          <br />
          <br />
          <span style={{ color: "#d95b5b" }}>{auth.errorMsg}</span>
        </form>
      </Card>

      <Toast ref={toast} />
    </div>
  );
};

export default LoginPage;
