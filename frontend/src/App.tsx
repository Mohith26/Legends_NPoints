import { Route, Routes } from "react-router-dom";
import Layout from "./components/Layout";
import TopicList from "./components/TopicList";
import TopicDetail from "./components/TopicDetail";
import MethodologyPage from "./components/MethodologyPage";

function App() {
  return (
    <Layout>
      <Routes>
        <Route path="/" element={<TopicList />} />
        <Route path="/topic/:id" element={<TopicDetail />} />
        <Route path="/methodology" element={<MethodologyPage />} />
      </Routes>
    </Layout>
  );
}

export default App;
