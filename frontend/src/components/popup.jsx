import { observer } from "mobx-react-lite";
import { useStore } from "../store/store-context";
import { useEffect } from "react";
import { useState } from "react";
import axios from "axios";
import RenameForm from "./rename-files";
import MoveForm from "./move-form";

const PopUp = observer(({ item, isFolder, onClose }) => {
  const { authStore } = useStore();
  const { fileStore } = useStore();
  const [isVisible, setIsVisible] = useState(false);
  const [showRenameForm, setShowRenameForm] = useState(false);
  const [isMoved, setIsMoved] = useState(false);

  const handleDownload = async () => {
    try {
      const response = await axios.get(`/api/file/download/${item.id}`, {
        headers: {
          Authorization: `Bearer ${authStore.token}`,
        },
        responseType: "blob",
      });

      if (response.status !== 200) {
        throw new Error(`Ошибка: ${response.status}`);
      }

      const filename = item.name;

      const blob = new Blob([response.data]);
      const downloadUrl = window.URL.createObjectURL(blob);
      const link = document.createElement("a");

      link.href = downloadUrl;
      link.download = filename;
      document.body.appendChild(link);
      link.click();

      window.URL.revokeObjectURL(downloadUrl);
      document.body.removeChild(link);
    } catch (error) {
      console.error("Ошибка при скачивании:", error);
      alert("Не удалось скачать файл");
    } finally {
      onClose();
    }
  };

  const handleDelete = async () => {
    try {
      if (isFolder) {
        await axios.delete(`/api/client/folder/${item.id}`, {
          headers: {
            Authorization: `Bearer ${authStore.token}`,
          },
        });
      } else {
        await axios.delete(`/api/file/delete/${item.id}`, {
          headers: {
            Authorization: `Bearer ${authStore.token}`,
          },
        });
      }
      fileStore.loadFiles(fileStore.currentFolder?.id);
      onClose();
    } catch (error) {
      console.error("Ошибка при удалении:", error);
      alert("Не удалось удалить файл");
    }
  };

  const handleRename = () => {
    setShowRenameForm(true);
    setIsVisible(false);
  };

  const handleMove = () => {
    setIsMoved(true);
    setIsVisible(false);
  };

  useEffect(() => {
    const handleClickOutside = (e) => {
      if (
        !showRenameForm &&
        !e.target.closest(".popup-side") &&
        !e.target.closest(".folder-form")
      ) {
        onClose();
      }
    };

    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, [onClose, showRenameForm]);

  useEffect(() => {
    const timer = setTimeout(() => {
      setIsVisible(true);
    }, 50);

    return () => clearTimeout(timer);
  }, []);

  return (
    <>
      {!showRenameForm && !isMoved && (
        <div className={`popup-side ${isVisible ? "visible" : ""}`}>
          <div className="popup-header">
            <h3 className="no-wrap-title">{item?.name}</h3>
          </div>
          <div className="popup-content">
            {!isFolder && (
              <span onClick={handleDownload} className="popup-btn">
                Скачать
              </span>
            )}
            <span onClick={handleDelete} className="popup-btn">
              Удалить
            </span>
            <span onClick={handleRename} className="popup-btn">
              Переименовать
            </span>
            <span onClick={handleMove} className="popup-btn">
              Переместить
            </span>
          </div>
        </div>
      )}
      {showRenameForm && (
        <RenameForm
          item={item}
          isFolder={isFolder}
          onClose={() => {
            setShowRenameForm(false);
            setIsVisible(true);
            onClose();
          }}
        />
      )}
      {isMoved && (
        <MoveForm
          item={item}
          isFolder={isFolder}
          onClose={() => {
            setIsMoved(false);
            setIsVisible(true);
            onClose();
          }}
        />
      )}
    </>
  );
});

export default PopUp;
