export const authenticatedFetch = async (url: string, options: RequestInit = {}) => {
  const token = typeof window !== 'undefined' ? localStorage.getItem("token") : null;
  const headers = {
    ...options.headers,
    'Authorization': token ? `Bearer ${token}` : '',
    'Content-Type': 'application/json'
  };
  
  const response = await fetch(url, { ...options, headers });
  
  if (response.status === 401 && typeof window !== 'undefined') {
    localStorage.removeItem("token");
    window.location.replace("/login");
  }
  
  return response;
};

export default authenticatedFetch;
