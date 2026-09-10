# Docker Buildx 多架构构建配置
# 用法: docker buildx bake -f docker-bake.hcl

variable "REGISTRY" {
  default = "ghcr.io/10000gd"
}

variable "IMAGE_NAME" {
  default = "china-criminal-prosecution-research"
}

variable "TAG" {
  default = "latest"
}

# 默认构建配置
target "default" {
  contexts = {
    # 使用alpine作为基础以减小镜像大小
  }
}

# 多架构构建目标
target "linux-amd64" {
  platforms = ["linux/amd64"]
  dockerfile = "Dockerfile.multiarch"
  tags = ["${REGISTRY}/${IMAGE_NAME}:${TAG}"]
  tags = ["${REGISTRY}/${IMAGE_NAME}:amd64-${TAG}"]
  output = ["type=docker"]
}

target "linux-arm64" {
  platforms = ["linux/arm64"]
  dockerfile = "Dockerfile.multiarch"
  tags = ["${REGISTRY}/${IMAGE_NAME}:arm64-${TAG}"]
  output = ["type=docker"]
}

target "linux-armv7" {
  platforms = ["linux/arm/v7"]
  dockerfile = "Dockerfile.multiarch"
  tags = ["${REGISTRY}/${IMAGE_NAME}:armv7-${TAG}"]
  output = ["type=docker"]
}

# 全平台构建 (需 docker buildx)
target "multi-platform" {
  platforms = ["linux/amd64", "linux/arm64", "linux/arm/v7"]
  dockerfile = "Dockerfile.multiarch"
  tags = ["${REGISTRY}/${IMAGE_NAME}:${TAG}"]
  tags = ["${REGISTRY}/${IMAGE_NAME}:v2.4.0"]
  output = ["type=registry"]
  cache-from = ["type=gha"]
  cache-to = ["type=gha,mode=max"]
}

# 单平台快速构建 (开发用)
target "dev" {
  dockerfile = "Dockerfile.multiarch"
  tags = ["${IMAGE_NAME}:dev"]
  output = ["type=docker"]
}
