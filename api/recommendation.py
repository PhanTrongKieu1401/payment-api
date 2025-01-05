import sys
import pandas as pd
import json
from sklearn.neighbors import NearestNeighbors
from sklearn.metrics.pairwise import cosine_similarity
import joblib
from io import StringIO
import hashlib
import os
import time

model_data_dir = 'model_data'
os.makedirs(model_data_dir, exist_ok=True)

similarity_matrix_file = os.path.join(model_data_dir, 'similarity_matrix.pkl')
user_product_matrix_file = os.path.join(model_data_dir, 'user_product_matrix.pkl')
checksum_file = os.path.join(model_data_dir, 'data_checksum.json')
last_update_time_file = os.path.join(model_data_dir, 'last_update_time.json')

def json_serializable(obj):
    if isinstance(obj, pd.Timestamp):
        return obj.isoformat()
    if isinstance(obj, pd.Series):
        return obj.tolist()
    if isinstance(obj, pd.DataFrame):
        return obj.to_dict()
    if isinstance(obj, pd.Int64Dtype):
        return int(obj)
    return str(obj)

def calculate_checksum(data):
    return hashlib.md5(json.dumps(data, sort_keys=True).encode('utf-8')).hexdigest()

def save_data_checksum(checksum):
    with open(checksum_file, 'w') as f:
        json.dump({'checksum': checksum}, f)

def load_data_checksum():
    if os.path.exists(checksum_file):
        with open(checksum_file, 'r') as f:
            return json.load(f)['checksum']
    return None

def save_last_update_time():
    update_time = time.time()
    with open(last_update_time_file, 'w') as f:
        json.dump({'last_update_time': update_time}, f)

# Đọc thời gian cập nhật dữ liệu
def load_last_update_time():
    if os.path.exists(last_update_time_file):
        with open(last_update_time_file, 'r') as f:
            return json.load(f)['last_update_time']
    return 0

def load_or_recompute_similarity_matrix(actions):
    # Tính toán lại user_product_matrix nếu cần thiết
    current_checksum = calculate_checksum(actions.to_dict())
    saved_checksum = load_data_checksum()

    if saved_checksum != current_checksum:
        # Tạo ma trận người dùng và sản phẩm nếu dữ liệu thay đổi
        user_product_matrix = actions.pivot_table(
            index='customerId', 
            columns='productId', 
            values='weight', 
            aggfunc='sum'
        ).fillna(0)

        # Tính toán ma trận tương đồng nếu dữ liệu thay đổi
        similarity_matrix = cosine_similarity(user_product_matrix)
        similarity_df = pd.DataFrame(
            similarity_matrix, 
            index=user_product_matrix.index, 
            columns=user_product_matrix.index
        )

        # Lưu ma trận tương đồng và user_product_matrix
        joblib.dump(similarity_matrix, similarity_matrix_file)
        joblib.dump(user_product_matrix, user_product_matrix_file)
        save_data_checksum(current_checksum)
        save_last_update_time()
    else:
        # Nếu dữ liệu không thay đổi, tải ma trận tương đồng và user_product_matrix đã lưu
        similarity_matrix = joblib.load(similarity_matrix_file)
        similarity_df = pd.DataFrame(similarity_matrix, index=joblib.load(user_product_matrix_file).index, columns=joblib.load(user_product_matrix_file).index)
        user_product_matrix = joblib.load(user_product_matrix_file)
    
    return similarity_df, user_product_matrix

try:
    data = sys.argv[1]
    actions = pd.read_json(StringIO(data))

    weight_map = {
        "PURCHASE": 1.0,
        "ADD_TO_CART": 0.7,
        "UPDATE_TO_CART": 0.5,
        "VIEW": 0.3
    }

    actions["weight"] = actions["actionType"].map(weight_map)

    current_checksum = calculate_checksum(actions.to_dict())
    saved_checksum = load_data_checksum()

    if saved_checksum != current_checksum:
        # Tạo ma trận người dùng và sản phẩm nếu dữ liệu thay đổi
        user_product_matrix = actions.pivot_table(
            index='customerId', 
            columns='productId', 
            values='weight', 
            aggfunc='sum'
        ).fillna(0)

        # Tính toán ma trận tương đồng nếu dữ liệu thay đổi
        similarity_matrix = cosine_similarity(user_product_matrix)
        similarity_df = pd.DataFrame(
            similarity_matrix, 
            index=user_product_matrix.index, 
            columns=user_product_matrix.index
        )

        # Lưu ma trận tương đồng và user_product_matrix
        joblib.dump(similarity_matrix, similarity_matrix_file)
        joblib.dump(user_product_matrix, user_product_matrix_file)
        save_data_checksum(current_checksum)
        save_last_update_time()

        # Gợi ý sản phẩm
        recommendations = []
        for user_id in user_product_matrix.index:
            # Lấy người dùng tương tự
            similar_users = similarity_df[user_id].sort_values(ascending=False).index[1:]
            
            # Gợi ý sản phẩm từ người dùng tương tự
            recommended_products = set()
            for similar_user in similar_users:
                similar_user_products = user_product_matrix.loc[similar_user]
                purchased_products = similar_user_products[similar_user_products > 0].index.tolist()
                recommended_products.update(purchased_products)
            
            # Loại bỏ sản phẩm đã mua bởi chính user
            user_purchased_products = user_product_matrix.loc[user_id]
            user_purchased_products = user_purchased_products[user_purchased_products > 0].index.tolist()
            recommended_products.difference_update(user_purchased_products)
            
            # Lấy 5 sản phẩm gợi ý
            top_recommended_products = list(recommended_products)[:5]

            recommendations.append({
                "customerId": user_id,
                "products": top_recommended_products
            })
        
        # Xuất kết quả
        print(json.dumps(recommendations, default=json_serializable))
    else:
        print(json.dumps([]))

except Exception as e:
    print(json.dumps({"error": str(e)}, default=json_serializable))
    sys.exit(1)