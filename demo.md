[ ] Screen recording video showing all the objects deployed in Kubernetes cluster. 
  [ ] Show all objects deployed and running. 
  [ ] Show an API call retrieving records from database. 
  [ ] Kill API microservice pod and show it regenerates. 
  [ ] Kill database pod and show it regenerates and keeps old data. 
  [ ] Demonstration of deployments, self-healing, persistence, deployment strategy, and FinOps considerations


curl http://136.68.44.58/api/v1/users
kubectl get all -n user-service
kubectl delete pod
watch -n2 'kubectl -n user-service get hpa,pods'
kubectl rollout restart deployment/user-service -n user-service
gcloud container clusters get-credentials k8s-labs-cluster --zone us-central1-a --project k8s-labs-500514

