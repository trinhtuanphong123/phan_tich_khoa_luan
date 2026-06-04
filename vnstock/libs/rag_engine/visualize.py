import os
import networkx as nx
from pyvis.network import Network
import click

# Cấu hình màu sắc cho đẹp (Style Báo cáo tài chính)
COLOR_MAP = {
    "HIGH_CONN": "#FF4500",  # Node quan trọng (nhiều kết nối): Màu cam đỏ
    "MEDIUM_CONN": "#1E90FF", # Node trung bình: Màu xanh dương
    "LOW_CONN": "#90EE90",    # Node ít kết nối: Màu xanh lá nhạt
    "TEXT": "#000000"
}

def find_graphml_file(ticker, year, quarter, base_dir="rag_storage"):
    """Tìm file graphml trong cấu trúc thư mục"""
    # Đường dẫn chuẩn: rag_storage/TICKER/YEAR/QUARTER/graph_chunk_entity_relation.graphml
    path = os.path.join(base_dir, ticker.upper(), str(year), quarter.upper(), "graph_chunk_entity_relation.graphml")
    
    if os.path.exists(path):
        return path
    else:
        print(f"❌ Không tìm thấy file đồ thị tại: {path}")
        return None

def create_visualization(graph_path, output_name="financial_graph.html"):
    print(f"loading graph from {graph_path}...")
    
    # 1. Load đồ thị từ file LightRAG
    G = nx.read_graphml(graph_path)
    print(f"📊 Thống kê: {G.number_of_nodes()} thực thể, {G.number_of_edges()} mối quan hệ.")

    # 2. Khởi tạo PyVis
    net = Network(height="750px", width="100%", bgcolor="#ffffff", font_color="black", select_menu=True, filter_menu=True)
    
    # 3. Tối ưu hiển thị (Vì đồ thị tài chính rất dày đặc)
    # Chỉ giữ lại các Node quan trọng nếu đồ thị quá lớn (>1000 nodes)
    if G.number_of_nodes() > 1000:
        print("⚠️ Đồ thị quá lớn, đang lọc bớt các node ít quan trọng...")
        degrees = dict(G.degree())
        # Chỉ giữ lại node có ít nhất 2 kết nối
        nodes_to_keep = [n for n, d in degrees.items() if d >= 2]
        G = G.subgraph(nodes_to_keep)

    # 4. Tô màu và gắn size cho Node dựa trên mức độ quan trọng (Degree)
    degrees = dict(G.degree())
    for node in G.nodes():
        deg = degrees.get(node, 1)
        
        # Gắn size: Càng nhiều kết nối càng to
        G.nodes[node]['size'] = 10 + (deg * 1.5)
        
        # Gắn title (khi hover chuột vào sẽ hiện chi tiết)
        desc = G.nodes[node].get('description', 'Không có mô tả')
        G.nodes[node]['title'] = f"Entity: {node}\nConnections: {deg}\nDesc: {desc}"

        # Tô màu
        if deg > 20:
            G.nodes[node]['color'] = COLOR_MAP["HIGH_CONN"]
        elif deg > 5:
            G.nodes[node]['color'] = COLOR_MAP["MEDIUM_CONN"]
        else:
            G.nodes[node]['color'] = COLOR_MAP["LOW_CONN"]

    # 5. Chuyển từ NetworkX sang PyVis
    net.from_nx(G)

    # 6. Cấu hình vật lý (Physics) để các node tự dàn trải đẹp mắt
    net.set_options("""
    var options = {
      "nodes": {
        "font": {
          "size": 16,
          "face": "tahoma"
        }
      },
      "edges": {
        "color": {
          "inherit": true
        },
        "smooth": false
      },
      "physics": {
        "forceAtlas2Based": {
          "gravitationalConstant": -50,
          "centralGravity": 0.01,
          "springLength": 100,
          "springConstant": 0.08
        },
        "maxVelocity": 50,
        "solver": "forceAtlas2Based",
        "timestep": 0.35,
        "stabilization": {
          "enabled": true,
          "iterations": 1000
        }
      }
    }
    """)

    # 7. Lưu file
    try:
        html_content = net.generate_html()
        with open(output_name, "w", encoding="utf-8") as f:
            f.write(html_content)
        print(f"✅ Đã tạo visualization thành công: {output_name}")
        print("👉 Hãy mở file HTML này bằng trình duyệt web.")
    except Exception as e:
        print(f"❌ Lỗi khi lưu file graph: {e}")

@click.command()
@click.argument('ticker')
@click.argument('year')
@click.argument('quarter')
def main(ticker, year, quarter):
    """Visualize Knowledge Graph của một mã chứng khoán."""
    path = find_graphml_file(ticker, year, quarter)
    if path:
        output_file = f"{ticker}_{year}_{quarter}_graph.html"
        create_visualization(path, output_file)

if __name__ == "__main__":
    main()