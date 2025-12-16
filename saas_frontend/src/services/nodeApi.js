import axios from 'axios';

export const createNodeApi = (nodeUrl, nodeSecret) => {
  // Ensure no trailing slash
  const baseURL = nodeUrl.replace(/\/$/, "");
  
  return axios.create({
    baseURL: baseURL,
    headers: {
      'x-node-secret': nodeSecret,
      'Content-Type': 'application/json'
    }
  });
};
