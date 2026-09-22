import { useState } from "react";
import { useStore } from "../../store/store-context";
import axios from "axios";

const CreFolder = () => {
  const { fileStore } = useStore();
  const [showForm, setShowForm] = useState(false);
  const [folderName, setFolderName] = useState("");
  const [error, setError] = useState("");
  const [isLoading, setIsLoading] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setIsLoading(true);

    if (!folderName.trim()) {
      setError("Название папки не может быть пустым");
      setIsLoading(false);
      return;
    }

    try {
      const response = await axios.post(
        `/api/client/folder/${fileStore.currentFolder.id}`,
        { name: folderName },
        {
          headers: {
            "Content-Type": "application/json",
          },
        }
      );

      if (response.status === 200) {
        setFolderName("");
        setShowForm(false);
        setError("");
        await fileStore.loadFiles(fileStore.currentFolder.id);
      }
    } catch (err) {
      if (axios.isAxiosError(err)) {
        setError(err.response?.data?.message || "Ошибка при создании папки");
      } else {
        setError("Неизвестная ошибка");
      }
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="folder-creator">
      <button
        className="upload-btn"
        onClick={() => setShowForm(true)}
        disabled={isLoading}
      >
        {isLoading ? "Создание..." : "Создать папку"}
      </button>

      {showForm && (
        <div className={`modal-overlay ${showForm ? "active" : ""}`}>
          <form onSubmit={handleSubmit} className="folder-form">
            <p>Введите название папки</p>
            <input
              type="text"
              value={folderName}
              onChange={(e) => {
                setFolderName(e.target.value);
                setError("");
              }}
              disabled={isLoading}
            />

            {error && <div className="error-message">{error}</div>}

            <div className="form-buttons">
              <button type="submit" disabled={isLoading}>
                {isLoading ? "Обработка..." : "Создать"}
              </button>
              <button
                type="button"
                onClick={() => {
                  setShowForm(false);
                  setError("");
                }}
                disabled={isLoading}
              >
                Отмена
              </button>
            </div>
          </form>
        </div>
      )}
    </div>
  );
};

export default CreFolder;
