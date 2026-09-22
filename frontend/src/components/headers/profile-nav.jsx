import { observer } from "mobx-react-lite";
import { useEffect, useState } from "react";
import profileLogo from "../../store/profile-logo";
import "../../../ProfileNav.css";
import { useNavigate } from "react-router-dom";
import { useStore } from "../../store/store-context";

const ProfileNav = observer(() => {
  const [isMenuOpen, setIsMenuOpen] = useState(false);
  const navigate = useNavigate();
  const { authStore } = useStore();
  const { fileStore } = useStore();

  useEffect(() => {
    profileLogo.getname();
  }, []);

  const handleNameClick = (e) => {
    e.preventDefault();
    setIsMenuOpen(!isMenuOpen);
  };

  const handleLogout = async () => {
    try {
      authStore.logout();
      fileStore.reset();
      navigate("/login");
      setIsMenuOpen(false);
    } catch (error) {
      console.error("Ошибка выхода:", error);
    }
  };

  const handleprofile = (e) => {
    e.preventDefault();
    navigate("/profile");
  };

  useEffect(() => {
    const handleClickOutside = (e) => {
      if (!e.target.closest(".user-menu")) {
        setIsMenuOpen(false);
      }
    };

    document.addEventListener("click", handleClickOutside);
    return () => document.removeEventListener("click", handleClickOutside);
  }, []);

  if (profileLogo.isLoading) {
    return <div>Loading user data...</div>;
  }

  if (profileLogo.error) {
    return <div>Error: {profileLogo.error}</div>;
  }

  return (
    <div className="user-menu">
      <div className="user-profile">
        <div
          className="username-container"
          onClick={handleNameClick}
          role="button"
          tabIndex={0}
        >
          <span className="username">{profileLogo.name}</span>
          <span className={`arrow ${isMenuOpen ? "open" : ""}`}>▼</span>
        </div>

        {isMenuOpen && (
          <div className="dropdown-menu">
            <div className="menu-item" onClick={handleprofile}>
              Профиль
            </div>
            <div className="menu-item" onClick={handleLogout}>
              Выйти
            </div>
          </div>
        )}
      </div>
    </div>
  );
});

export default ProfileNav;
