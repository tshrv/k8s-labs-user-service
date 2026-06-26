[x] Screen recording video showing all the objects deployed in Kubernetes cluster. 
  [x] Show all objects deployed and running. 
  [x] Show an API call retrieving records from database. 
  [x] Kill API microservice pod and show it regenerates. 
  [x] Kill database pod and show it regenerates and keeps old data. 
  [x] Demonstration of deployments
  [x] self-healing
  [x] persistence
  [x] deployment strategy
  [x] FinOps considerations


curl http://136.68.44.58/api/v1/users
kubectl get all -n user-service
kubectl get pods -n user-service
kubectl delete pod
watch -n2 'kubectl -n user-service get hpa,pods'
kubectl rollout restart deployment/user-service -n user-service
gcloud container clusters get-credentials k8s-labs-cluster --zone us-central1-a --project k8s-labs-500514

records t1
"total": 2255,
