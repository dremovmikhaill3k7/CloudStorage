import axios from "axios";
import { observer } from "mobx-react-lite";
import { useState } from "react";
import { useStore } from "../store/store-context";

const MoveForm = observer(({ item, isFolder, onClose }) => {
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState("");
  const { authStore, fileStore } = useStore();
  const [path, setPath] = useState("");

  const handlepath = async (e) => {
    e.preventDefault();
    const response = await axios.get(`/api/resolve-path/${path}`, {
      headers: {
        Authorization: `Bearer ${authStore.token}`,
      },
    });
    if (response.status === 200) {
      handleSubmit(e, response.data.folder_id);
    }
  };

  const handleSubmit = async (e, pfolderid) => {
    e.preventDefault();
    setIsLoading(true);

    try {
      const endpoint = isFolder
        ? `/api/client/folder/${item.id}`
        : `/api/file/update/${item.id}`;

      await axios.patch(
        endpoint,
        { parent_folder_id: pfolderid },
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
        setError(error.response?.data?.message || "Ошибка при перемещении");
      } else {
        setError("Неизвестная ошибка");
      }
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="modal-overlay active">
      <form onSubmit={handlepath} className="folder-form">
        <p>Укажите путь к папке с /disk/...</p>
        <input
          type="text"
          value={path}
          onChange={(e) => {
            setPath(e.target.value);
            setError("");
          }}
          disabled={isLoading}
        />

        {error && <div className="error-message">{error}</div>}

        <div className="form-buttons">
          <button type="submit" disabled={isLoading}>
            {isLoading ? "Обработка..." : "Переместить"}{" "}
          </button>
          <button type="button" onClick={onClose} disabled={isLoading}>
            Отмена
          </button>
        </div>
      </form>
    </div>
  );
});

export default MoveForm;
