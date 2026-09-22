import axios from "axios";
import { observer } from "mobx-react-lite";
import { useState } from "react";
import { useStore } from "../store/store-context";

const RenameForm = observer(({ item, isFolder, onClose }) => {
  const [newName, setNewName] = useState(item.name);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState("");
  const { authStore, fileStore } = useStore();

  const handleSubmit = async (e) => {
    e.preventDefault();
    setIsLoading(true);

    if (!newName.trim()) {
      setError("Название не может быть пустым");
      setIsLoading(false);
      return;
    }

    try {
      const endpoint = isFolder
        ? `/api/client/folder/${item.id}`
        : `/api/file/update/${item.id}`;

      await axios.patch(
        endpoint,
        { name: newName },
        {
          headers: {
            Authorization: `Bearer ${authStore.token}`,
          },
        }
      );

      fileStore.loadFiles(fileStore.currentFolder?.id);
      onClose();
    } catch (error) {
      if (axios.isAxiosError(error)) {
        setError(error.response?.data?.message || "Ошибка при переименовании");
      } else {
        setError("Неизвестная ошибка");
      }
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="modal-overlay active">
      <form onSubmit={handleSubmit} className="folder-form">
        <p>Новое название {isFolder ? "папки" : "файла"}</p>
        <input
          type="text"
          value={newName}
          onChange={(e) => {
            setNewName(e.target.value);
            setError("");
          }}
          disabled={isLoading}
        />

        {error && <div className="error-message">{error}</div>}

        <div className="form-buttons">
          <button type="submit" disabled={isLoading}>
            {isLoading ? "Обработка..." : "Переименовать"}{" "}
          </button>
          <button type="button" onClick={onClose} disabled={isLoading}>
            Отмена
          </button>
        </div>
      </form>
    </div>
  );
});

export default RenameForm;
