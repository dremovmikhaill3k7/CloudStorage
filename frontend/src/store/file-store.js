import { makeAutoObservable, runInAction, computed } from "mobx";
import axios from "axios";

class FileStore {
  files = [];
  folders = [];
  currentFolder = null;
  rootFolderId = null;
  folderParentId = null;
  isLoading = false;
  error = null;
  searchQuery = "";
  weight = 0;

  constructor(authStore) {
    makeAutoObservable(this, {
      filteredFiles: computed,
      filteredFolders: computed,
    });
    this.authStore = authStore;
  }

  reset = () => {
    runInAction(() => {
      this.currentFolder = null;
      this.folderParentId = null;
      this.rootFolderId = null;
      this.weight = 0;
      this.files = [];
      this.folders = [];
      this.isLoading = false;
      this.error = null;
    });
  };

  setSearchQuery = (query) => {
    this.searchQuery = query;
  };

  get filteredFiles() {
    return this.files.filter((file) =>
      file.name.toLowerCase().includes(this.searchQuery.toLowerCase())
    );
  }

  get filteredFolders() {
    return this.folders.filter((folder) =>
      folder.name.toLowerCase().includes(this.searchQuery.toLowerCase())
    );
  }

  loadFiles = async (folderId = null) => {
    try {
      runInAction(() => {
        this.isLoading = true;
        this.error = null;
      });

      const url = folderId
        ? `api/client/folder/${folderId}/`
        : "api/client/disk/";

      const response = await axios.get(url, {
        headers: {
          Authorization: `Bearer ${this.authStore.token}`,
        },
      });

      runInAction(() => {
        this.files = response.data.files;
        this.folders = response.data.subfolders;
        this.currentFolder = response.data.current_folder;
        if (!folderId) {
          this.rootFolderId = response.data.current_folder.id;
        }
        this.weight = response.data.weight;
        this.folderParentId = response.data.folder_parent_id;
        this.isLoading = false;
      });
    } catch (error) {
      runInAction(() => {
        this.error = error.response?.data?.message || error.message;
        this.isLoading = false;

        if (error.response?.status === 401) {
          this.authStore.logout();
        }
      });
      throw error;
    }
  };
}

export default FileStore;
