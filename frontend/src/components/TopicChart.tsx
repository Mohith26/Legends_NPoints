import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  CartesianGrid,
} from "recharts";
import type { TopicSummary } from "../types";

interface TopicChartProps {
  topics: TopicSummary[];
}

function TopicChart({ topics }: TopicChartProps) {
  const chartData = topics.map((t) => ({
    name: t.gpt_label || `Topic ${t.rank}`,
    posts: t.post_count,
    avgUpvotes: Math.round(t.avg_upvotes),
  }));

  return (
    <ResponsiveContainer width="100%" height={Math.max(400, topics.length * 32)}>
      <BarChart data={chartData} layout="vertical" margin={{ left: 160 }}>
        <CartesianGrid strokeDasharray="3 3" horizontal={false} />
        <XAxis type="number" />
        <YAxis
          type="category"
          dataKey="name"
          width={150}
          tick={{ fontSize: 12 }}
        />
        <Tooltip />
        <Bar dataKey="posts" fill="#4f46e5" radius={[0, 4, 4, 0]} />
      </BarChart>
    </ResponsiveContainer>
  );
}

export default TopicChart;
