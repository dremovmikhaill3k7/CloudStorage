import { BrowserRouter, Routes, Route } from "react-router-dom";
import { StoreProvider } from "./store/store-context";
import Filelist from "./components/file-list";
import LoginForm from "./components/login-form";
import AuthWrapper from "./components/auth-wrapper";
import Header from "./components/headers/header";
import RegistrationForm from "./components/registration-form";
import HeadProfile from "./components/profile/hed_profile.jsx";
import Userinfo from "./components/profile/userinfo.jsx";

function App() {
  return (
    <StoreProvider>
      <BrowserRouter>
        <Routes>
          <Route
            path="/"
            element={
              <AuthWrapper>
                <Header></Header>
                <div className="maininfo">
                  <Filelist />
                </div>
              </AuthWrapper>
            }
          />
          <Route
            path="/profile"
            element={
              <div>
                <HeadProfile />
                <div className="maininfo">
                  <Userinfo />
                </div>
              </div>
            }
          />
          <Route path="/Registration" element={<RegistrationForm />} />
          <Route path="/login" element={<LoginForm />} />
          <Route path="*" element={<h1>Not found</h1>} />
        </Routes>
      </BrowserRouter>
    </StoreProvider>
  );
}

export default App;
