import client from '@/lib/apiClient'; // Assuming we create this

export const fetchStats = async () => {
  const res = await client('/api/dashboard/stats');
  return res.json();
};

// ... and so on
