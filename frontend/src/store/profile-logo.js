import { makeAutoObservable } from "mobx";
import axios from "axios";

class ProfileLogo {
    name = "";
    
    isLoading = false;
    error = null;

    constructor() {
        makeAutoObservable(this);
    }

    getname = async () => {
        try {
            this.isLoading = true;
            const response = await axios.get('/api/user');
            
            this.name = response.data.username;
            
            this.error = null;
            console.log("Username received:", this.name);
        } catch (error) {
            console.error("Error fetching username:", error);
            this.error = error.response?.data?.message || "Failed to get username";
            this.name = ""; 
        } finally {
            this.isLoading = false;
        }
    }
}

export default new ProfileLogo();