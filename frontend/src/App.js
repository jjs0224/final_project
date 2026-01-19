import './App.css';
import { Routes, Route, Navigate } from "react-router-dom";
import Homepage from "./pages/HomePage.jsx";
import CommunityPage from "./pages/CommunityPage.jsx";
import LoginPage from "./pages/LoginPage.jsx";
import ProfilePage from "./pages/ProfilePage.jsx";
import ReviewPage from "./pages/ReviewPage.jsx";
import ReviewWritePage from "./pages/ReviewWritePage.jsx";
import SignupPage from "./pages/SignupPage.jsx"
import Admin from "./pages/Admin.jsx"

function App() {
  return (
      <Routes>
        <Route path="/" element={<Homepage />} />
        <Route path="/community" element={<CommunityPage />} />
        <Route path="/login" element={<LoginPage />} />
        <Route path="/profile/:memberid" element={<ProfilePage />} />
        <Route path="/profile" element={<Navigate to="/login" replace />} />
        <Route path="/review" element={<ReviewPage />} />
        <Route path="/review/new" element={<ReviewWritePage />} />
        <Route path="/signup" element={<SignupPage />} />z
        <Route path="/admin" element={<Admin />} />z
      </Routes>
  )
};

export default App;
